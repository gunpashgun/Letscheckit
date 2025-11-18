/**
 * Apify Actor для анализа Instagram Reels
 * 
 * Анализирует видео: ASR (речь), OCR (текст на экране), Visual Events
 * Использует OpenRouter API для всех анализов
 */

import { Actor } from 'apify';
import fetch from 'node-fetch';
import FormData from 'form-data';
import fs from 'fs';
import path from 'path';

// Конфигурация моделей OpenRouter
const MODELS = {
    ASR: 'openai/gpt-4o-audio-preview',
    OCR: 'anthropic/claude-3.5-sonnet',
    VISUAL: 'meta-llama/llama-3.2-90b-vision-instruct'
};

await Actor.main(async () => {
    // Получаем input
    const input = await Actor.getInput();
    
    if (!input) {
        throw new Error('Input is required!');
    }
    
    const {
        reel_id,
        video_url,
        caption = '',
        hashtags = [],
        analysis_window_seconds = 5,
        ocr_times = [0.2, 1.0, 2.0, 3.0, 4.0],
        openrouter_api_key
    } = input;
    
    Actor.log.info(`Начало анализа рилса: ${reel_id}`);
    Actor.log.info(`Video URL: ${video_url}`);
    
    // Проверяем наличие API ключа
    const apiKey = openrouter_api_key || process.env.OPENROUTER_API_KEY;
    if (!apiKey) {
        throw new Error('OpenRouter API key is required! Set OPENROUTER_API_KEY or pass openrouter_api_key in input');
    }
    
    try {
        // 1. Скачиваем видео
        Actor.log.info('Скачивание видео...');
        const videoPath = await downloadVideo(video_url);
        Actor.log.info(`Видео скачано: ${videoPath}`);
        
        // 2. Извлекаем аудио (первые N секунд)
        Actor.log.info(`Извлечение аудио (${analysis_window_seconds}s)...`);
        const audioPath = await extractAudio(videoPath, analysis_window_seconds);
        Actor.log.info(`Аудио извлечено: ${audioPath}`);
        
        // 3. ASR - распознавание речи через OpenRouter
        Actor.log.info('ASR анализ через OpenRouter...');
        const speechSegments = await transcribeAudio(audioPath, apiKey);
        Actor.log.info(`Распознано ${speechSegments.length} сегментов речи`);
        
        // 4. OCR - текст на экране через OpenRouter
        Actor.log.info('OCR анализ через OpenRouter...');
        const onscreenTextSegments = await analyzeOCR(videoPath, ocr_times, apiKey);
        Actor.log.info(`Извлечено ${onscreenTextSegments.length} текстовых сегментов`);
        
        // 5. Visual Events - визуальные события через OpenRouter
        Actor.log.info('Анализ визуальных событий через OpenRouter...');
        const visualEvents = await analyzeVisualEvents(videoPath, ocr_times, apiKey);
        Actor.log.info(`Обнаружено ${visualEvents.length} визуальных событий`);
        
        // 6. Сохраняем результаты
        const results = {
            reel_id,
            speech_segments: speechSegments,
            onscreen_text_segments: onscreenTextSegments,
            visual_events: visualEvents,
            metadata: {
                caption,
                hashtags,
                analysis_window_seconds,
                timestamp: new Date().toISOString()
            }
        };
        
        await Actor.pushData(results);
        Actor.log.info('✅ Анализ завершён успешно!');
        
        // Очистка временных файлов
        cleanupFiles([videoPath, audioPath]);
        
    } catch (error) {
        Actor.log.error(`❌ Ошибка анализа: ${error.message}`);
        throw error;
    }
});

/**
 * Скачивает видео по URL
 */
async function downloadVideo(videoUrl) {
    const videoPath = path.join(Actor.apifyClient ? '/tmp' : '.', `video_${Date.now()}.mp4`);
    
    const response = await fetch(videoUrl, {
        headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    });
    
    if (!response.ok) {
        throw new Error(`Failed to download video: ${response.status} ${response.statusText}`);
    }
    
    const buffer = await response.buffer();
    fs.writeFileSync(videoPath, buffer);
    
    return videoPath;
}

/**
 * Извлекает аудио из видео используя ffmpeg
 */
async function extractAudio(videoPath, duration) {
    const audioPath = videoPath.replace('.mp4', '.wav');
    
    // Используем ffmpeg через child_process
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execPromise = promisify(exec);
    
    const command = `ffmpeg -i "${videoPath}" -ss 0 -t ${duration} -vn -acodec pcm_s16le -ar 16000 -ac 1 -y "${audioPath}"`;
    
    try {
        await execPromise(command);
        return audioPath;
    } catch (error) {
        throw new Error(`FFmpeg error: ${error.message}`);
    }
}

/**
 * Транскрибирует аудио через OpenRouter GPT-4o Audio
 */
async function transcribeAudio(audioPath, apiKey) {
    // Читаем аудио и конвертируем в base64
    const audioBuffer = fs.readFileSync(audioPath);
    const audioBase64 = audioBuffer.toString('base64');
    
    const systemPrompt = `You are a speech recognition expert. Transcribe the audio to text with timestamps.
Return JSON array with segments: [{"start": 0.0, "end": 1.5, "text": "transcribed text"}, ...]
Return ONLY valid JSON array, no additional text.`;
    
    const userPrompt = 'Transcribe this audio segment with timestamps. Return JSON array of segments.';
    
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            model: MODELS.ASR,
            messages: [
                {
                    role: 'system',
                    content: systemPrompt
                },
                {
                    role: 'user',
                    content: [
                        { type: 'text', text: userPrompt },
                        {
                            type: 'input_audio',
                            input_audio: {
                                data: audioBase64,
                                format: 'wav'
                            }
                        }
                    ]
                }
            ],
            temperature: 0.0
        })
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`OpenRouter ASR error: ${response.status} - ${errorText}`);
    }
    
    const data = await response.json();
    const content = data.choices[0].message.content.trim();
    
    // Парсим JSON из ответа
    const jsonMatch = content.match(/\[[\s\S]*\]/);
    if (jsonMatch) {
        try {
            const segments = JSON.parse(jsonMatch[0]);
            return Array.isArray(segments) ? segments : [];
        } catch (e) {
            Actor.log.warning(`Failed to parse ASR JSON: ${e.message}`);
            return [];
        }
    }
    
    return [];
}

/**
 * Анализирует текст на экране через OpenRouter Vision
 */
async function analyzeOCR(videoPath, times, apiKey) {
    const results = [];
    
    for (const time of times) {
        try {
            const frameBase64 = await extractFrameAsBase64(videoPath, time);
            
            const systemPrompt = `You are an OCR expert. Extract all visible text from the image. 
Return ONLY the text content, no explanations or additional text. 
If there's no text, return empty string.`;
            
            const userPrompt = `Extract all text visible in this frame at time ${time}s. Return only the text content.`;
            
            const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${apiKey}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model: MODELS.OCR,
                    messages: [
                        {
                            role: 'user',
                            content: [
                                { type: 'text', text: `${systemPrompt}\n\n${userPrompt}` },
                                { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${frameBase64}` } }
                            ]
                        }
                    ],
                    temperature: 0.1
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                const text = data.choices[0].message.content.trim();
                
                if (text) {
                    results.push({ time, text });
                }
            }
        } catch (error) {
            Actor.log.warning(`OCR error at ${time}s: ${error.message}`);
        }
    }
    
    return results;
}

/**
 * Анализирует визуальные события через OpenRouter Vision
 */
async function analyzeVisualEvents(videoPath, times, apiKey) {
    // Извлекаем кадры
    const frames = [];
    for (const time of times.slice(0, 3)) { // Ограничиваем 3 кадрами для API
        try {
            const frameBase64 = await extractFrameAsBase64(videoPath, time);
            frames.push({ time, base64: frameBase64 });
        } catch (error) {
            Actor.log.warning(`Frame extraction error at ${time}s: ${error.message}`);
        }
    }
    
    if (frames.length === 0) {
        return [];
    }
    
    const systemPrompt = `You are analyzing Instagram reel frames to detect visual events.
For each frame, identify:
1. FACE_CLOSEUP - if there's a face in close-up
2. BIG_TEXT - if there's large text covering most of the screen
3. LOGO_OR_BRAND_OBJECT - if there's a logo, brand packaging, or distinctive brand element visible
4. SCENE_CHANGE - if this frame is significantly different from previous

Return JSON array:
[
  {"time": 0.2, "events": ["FACE_CLOSEUP"]},
  {"time": 1.0, "events": ["BIG_TEXT"]},
  ...
]`;
    
    const userPrompt = `Analyze these ${frames.length} frames at times: ${frames.map(f => f.time)}.
Detect visual events: FACE_CLOSEUP, BIG_TEXT, LOGO_OR_BRAND_OBJECT, SCENE_CHANGE.
Return JSON array.`;
    
    const fullPrompt = `${systemPrompt}\n\n${userPrompt}`;
    
    const contentParts = [{ type: 'text', text: fullPrompt }];
    for (const frame of frames) {
        contentParts.push({
            type: 'image_url',
            image_url: { url: `data:image/jpeg;base64,${frame.base64}` }
        });
    }
    
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            model: MODELS.VISUAL,
            messages: [{ role: 'user', content: contentParts }],
            temperature: 0.3
        })
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`OpenRouter Visual error: ${response.status} - ${errorText}`);
    }
    
    const data = await response.json();
    const content = data.choices[0].message.content.trim();
    
    // Парсим JSON из ответа
    const jsonMatch = content.match(/\[[\s\S]*\]/);
    if (jsonMatch) {
        try {
            const eventsData = JSON.parse(jsonMatch[0]);
            const results = [];
            
            if (Array.isArray(eventsData)) {
                for (const item of eventsData) {
                    if (item.events && Array.isArray(item.events)) {
                        for (const event of item.events) {
                            results.push({ time: item.time, event });
                        }
                    }
                }
            }
            
            return results;
        } catch (e) {
            Actor.log.warning(`Failed to parse Visual Events JSON: ${e.message}`);
            return [];
        }
    }
    
    return [];
}

/**
 * Извлекает кадр из видео в указанное время и возвращает base64
 */
async function extractFrameAsBase64(videoPath, time) {
    const framePath = videoPath.replace('.mp4', `_frame_${time}.jpg`);
    
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execPromise = promisify(exec);
    
    const command = `ffmpeg -ss ${time} -i "${videoPath}" -vframes 1 -q:v 2 -y "${framePath}"`;
    
    await execPromise(command);
    
    const frameBuffer = fs.readFileSync(framePath);
    const frameBase64 = frameBuffer.toString('base64');
    
    // Удаляем временный кадр
    fs.unlinkSync(framePath);
    
    return frameBase64;
}

/**
 * Очищает временные файлы
 */
function cleanupFiles(files) {
    for (const file of files) {
        try {
            if (fs.existsSync(file)) {
                fs.unlinkSync(file);
                Actor.log.info(`Удалён временный файл: ${file}`);
            }
        } catch (error) {
            Actor.log.warning(`Не удалось удалить файл ${file}: ${error.message}`);
        }
    }
}

