/**
 * Apify Actor для анализа Instagram Reels
 * 
 * Режимы работы:
 * 1. Single - анализ одного рилса
 * 2. Supabase Batch - массовый анализ из Supabase БД
 */

import { Actor } from 'apify';
import { createClient } from '@supabase/supabase-js';
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
    const input = await Actor.getInput();
    
    if (!input) {
        throw new Error('Input is required!');
    }
    
    const mode = input.mode || 'single';
    const apiKey = input.openrouter_api_key || process.env.OPENROUTER_API_KEY;
    
    if (!apiKey) {
        throw new Error('OpenRouter API key is required!');
    }
    
    Actor.log.info(`Режим работы: ${mode}`);
    
    if (mode === 'supabase_batch') {
        await processBatchFromSupabase(input, apiKey);
    } else {
        await processSingleReel(input, apiKey);
    }
});

/**
 * Режим: Batch from Supabase
 * Получает список reels из Supabase и обрабатывает их
 */
async function processBatchFromSupabase(input, apiKey) {
    const {
        supabase_url,
        supabase_key,
        batch_limit = 10,
        filter_unanalyzed_only = true,
        analysis_window_seconds = 5,
        ocr_times = [0.2, 1.0, 2.0, 3.0, 4.0]
    } = input;
    
    if (!supabase_url || !supabase_key) {
        throw new Error('supabase_url and supabase_key are required for batch mode!');
    }
    
    Actor.log.info('Подключение к Supabase...');
    const supabase = createClient(supabase_url, supabase_key);
    
    // Получаем список reels для обработки
    Actor.log.info(`Получение списка reels (limit: ${batch_limit}, unanalyzed_only: ${filter_unanalyzed_only})...`);
    
    let query = supabase
        .from('reels')
        .select('id, source_video_url, storage_video_path, caption, hashtags, url')
        .not('storage_video_path', 'is', null)
        .limit(batch_limit);
    
    // Если нужны только неанализированные
    if (filter_unanalyzed_only) {
        // Проверяем наличие записи в reel_analysis_raw
        const { data: analyzed, error: analyzedError } = await supabase
            .from('reel_analysis_raw')
            .select('reel_id');
        
        if (!analyzedError && analyzed) {
            const analyzedIds = analyzed.map(r => r.reel_id);
            query = query.not('id', 'in', `(${analyzedIds.join(',')})`);
        }
    }
    
    const { data: reels, error } = await query;
    
    if (error) {
        throw new Error(`Supabase error: ${error.message}`);
    }
    
    if (!reels || reels.length === 0) {
        Actor.log.info('Нет reels для обработки');
        return;
    }
    
    Actor.log.info(`Найдено ${reels.length} reels для анализа`);
    
    // Обрабатываем каждый reel
    for (let i = 0; i < reels.length; i++) {
        const reel = reels[i];
        Actor.log.info(`\n[${i + 1}/${reels.length}] Обработка reel: ${reel.id}`);
        
        try {
            // Формируем video_url
            const video_url = reel.storage_video_path
                ? `${supabase_url}/storage/v1/object/public/reels/${reel.storage_video_path}`
                : reel.source_video_url;
            
            // Анализируем
            const result = await analyzeReel({
                reel_id: reel.id,
                video_url,
                caption: reel.caption || '',
                hashtags: reel.hashtags || [],
                analysis_window_seconds,
                ocr_times
            }, apiKey);
            
            // Сохраняем результаты в Supabase
            await saveResultsToSupabase(supabase, reel.id, result);
            
            Actor.log.info(`✅ Reel ${reel.id} обработан успешно`);
            
        } catch (error) {
            Actor.log.error(`❌ Ошибка обработки reel ${reel.id}: ${error.message}`);
            // Продолжаем обработку следующих
        }
    }
    
    Actor.log.info(`\n🎉 Batch обработка завершена: ${reels.length} reels`);
}

/**
 * Режим: Single Reel
 * Обрабатывает один рилс
 */
async function processSingleReel(input, apiKey) {
    const {
        reel_id,
        video_url,
        caption = '',
        hashtags = [],
        analysis_window_seconds = 5,
        ocr_times = [0.2, 1.0, 2.0, 3.0, 4.0]
    } = input;
    
    if (!reel_id || !video_url) {
        throw new Error('reel_id and video_url are required for single mode!');
    }
    
    Actor.log.info(`Анализ рилса: ${reel_id}`);
    Actor.log.info(`Video URL: ${video_url}`);
    
    const result = await analyzeReel({
        reel_id,
        video_url,
        caption,
        hashtags,
        analysis_window_seconds,
        ocr_times
    }, apiKey);
    
    // Сохраняем в Apify Dataset
    await Actor.pushData(result);
    
    Actor.log.info('✅ Анализ завершён успешно!');
}

/**
 * Основная функция анализа рилса
 */
async function analyzeReel(params, apiKey) {
    const { reel_id, video_url, caption, hashtags, analysis_window_seconds, ocr_times } = params;
    
    // 1. Скачиваем видео
    Actor.log.info('Скачивание видео...');
    const videoPath = await downloadVideo(video_url);
    
    // 2. Извлекаем аудио
    Actor.log.info(`Извлечение аудио (${analysis_window_seconds}s)...`);
    const audioPath = await extractAudio(videoPath, analysis_window_seconds);
    
    // 3. ASR - распознавание речи
    Actor.log.info('ASR анализ...');
    const speechSegments = await transcribeAudio(audioPath, apiKey);
    Actor.log.info(`Распознано ${speechSegments.length} сегментов речи`);
    
    // 4. OCR - текст на экране
    Actor.log.info('OCR анализ...');
    const onscreenTextSegments = await analyzeOCR(videoPath, ocr_times, apiKey);
    Actor.log.info(`Извлечено ${onscreenTextSegments.length} текстовых сегментов`);
    
    // 5. Visual Events
    Actor.log.info('Анализ визуальных событий...');
    const visualEvents = await analyzeVisualEvents(videoPath, ocr_times, apiKey);
    Actor.log.info(`Обнаружено ${visualEvents.length} визуальных событий`);
    
    // Очистка
    cleanupFiles([videoPath, audioPath]);
    
    return {
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
}

/**
 * Сохраняет результаты анализа в Supabase
 */
async function saveResultsToSupabase(supabase, reel_id, results) {
    const speech_text = results.speech_segments.map(s => s.text).join(' ');
    const screen_text = results.onscreen_text_segments.map(s => s.text).join(' ');
    const caption_intro = results.metadata.caption.split('\n')[0] || '';
    const hook_raw_text = `${speech_text} | ${screen_text} | ${caption_intro}`.trim();
    
    const analysis_context = {
        window_seconds: results.metadata.analysis_window_seconds,
        speech_segments: results.speech_segments,
        onscreen_text_segments: results.onscreen_text_segments,
        visual_events: results.visual_events,
        caption_intro,
        hashtags: results.metadata.hashtags,
        source: 'apify_actor'
    };
    
    const record = {
        reel_id,
        speech_text,
        screen_text,
        caption_hook_text: caption_intro,
        hook_raw_text,
        speech_segments: results.speech_segments,
        onscreen_text_segments: results.onscreen_text_segments,
        visual_events: results.visual_events,
        analysis_context
    };
    
    // Проверяем существование записи
    const { data: existing } = await supabase
        .from('reel_analysis_raw')
        .select('id')
        .eq('reel_id', reel_id);
    
    if (existing && existing.length > 0) {
        await supabase
            .from('reel_analysis_raw')
            .update(record)
            .eq('reel_id', reel_id);
        Actor.log.info('Результаты обновлены в Supabase');
    } else {
        await supabase
            .from('reel_analysis_raw')
            .insert(record);
        Actor.log.info('Результаты сохранены в Supabase');
    }
}

/**
 * Скачивает видео
 */
async function downloadVideo(videoUrl) {
    const videoPath = path.join('/tmp', `video_${Date.now()}.mp4`);
    
    const response = await fetch(videoUrl, {
        headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    });
    
    if (!response.ok) {
        throw new Error(`Failed to download video: ${response.status}`);
    }
    
    const buffer = await response.buffer();
    fs.writeFileSync(videoPath, buffer);
    
    return videoPath;
}

/**
 * Извлекает аудио из видео
 */
async function extractAudio(videoPath, duration) {
    const audioPath = videoPath.replace('.mp4', '.wav');
    
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execPromise = promisify(exec);
    
    const command = `ffmpeg -i "${videoPath}" -ss 0 -t ${duration} -vn -acodec pcm_s16le -ar 16000 -ac 1 -y "${audioPath}"`;
    
    await execPromise(command);
    return audioPath;
}

/**
 * Транскрибирует аудио через OpenRouter
 */
async function transcribeAudio(audioPath, apiKey) {
    const audioBuffer = fs.readFileSync(audioPath);
    const audioBase64 = audioBuffer.toString('base64');
    
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
                    content: 'You are a speech recognition expert. Return JSON array: [{"start": 0.0, "end": 1.5, "text": "..."}]'
                },
                {
                    role: 'user',
                    content: [
                        { type: 'text', text: 'Transcribe with timestamps. Return JSON array.' },
                        { type: 'input_audio', input_audio: { data: audioBase64, format: 'wav' } }
                    ]
                }
            ],
            temperature: 0.0
        })
    });
    
    if (!response.ok) {
        throw new Error(`ASR error: ${response.status}`);
    }
    
    const data = await response.json();
    const content = data.choices[0].message.content.trim();
    const jsonMatch = content.match(/\[[\s\S]*\]/);
    
    if (jsonMatch) {
        try {
            return JSON.parse(jsonMatch[0]);
        } catch (e) {
            return [];
        }
    }
    
    return [];
}

/**
 * OCR анализ кадров
 */
async function analyzeOCR(videoPath, times, apiKey) {
    const results = [];
    
    for (const time of times) {
        try {
            const frameBase64 = await extractFrameAsBase64(videoPath, time);
            
            const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${apiKey}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model: MODELS.OCR,
                    messages: [{
                        role: 'user',
                        content: [
                            { type: 'text', text: 'Extract all text from this image. Return only the text.' },
                            { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${frameBase64}` } }
                        ]
                    }],
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
 * Анализ визуальных событий
 */
async function analyzeVisualEvents(videoPath, times, apiKey) {
    const frames = [];
    
    for (const time of times.slice(0, 3)) {
        try {
            const frameBase64 = await extractFrameAsBase64(videoPath, time);
            frames.push({ time, base64: frameBase64 });
        } catch (error) {
            Actor.log.warning(`Frame error at ${time}s: ${error.message}`);
        }
    }
    
    if (frames.length === 0) return [];
    
    const contentParts = [{
        type: 'text',
        text: `Analyze frames at times ${frames.map(f => f.time)}. Detect: FACE_CLOSEUP, BIG_TEXT, LOGO_OR_BRAND_OBJECT, SCENE_CHANGE. Return JSON: [{"time": 0.2, "events": ["FACE_CLOSEUP"]}, ...]`
    }];
    
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
        throw new Error(`Visual error: ${response.status}`);
    }
    
    const data = await response.json();
    const content = data.choices[0].message.content.trim();
    const jsonMatch = content.match(/\[[\s\S]*\]/);
    
    if (jsonMatch) {
        try {
            const eventsData = JSON.parse(jsonMatch[0]);
            const results = [];
            
            for (const item of eventsData) {
                if (item.events) {
                    for (const event of item.events) {
                        results.push({ time: item.time, event });
                    }
                }
            }
            
            return results;
        } catch (e) {
            return [];
        }
    }
    
    return [];
}

/**
 * Извлекает кадр из видео
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
            }
        } catch (error) {
            Actor.log.warning(`Cleanup error: ${error.message}`);
        }
    }
}
