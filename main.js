/**
 * Apify Actor для анализа Instagram Reels
 * 
 * Режимы работы:
 * 1. Single - анализ одного рилса
 * 2. Supabase Batch - массовый анализ из Supabase БД
 */

import { Actor, log } from 'apify';
import { createClient } from '@supabase/supabase-js';
import { google } from 'googleapis';
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
    
    log.info(`Режим работы: ${mode}`);
    
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
        batch_limit = 10,
        filter_unanalyzed_only = true,
        analysis_window_seconds = 5,
        ocr_times = [0.2, 1.0, 2.0, 3.0, 4.0]
    } = input;
    
    // Получаем Supabase credentials из input или Environment variables
    const supabase_url = input.supabase_url || process.env.SUPABASE_URL;
    const supabase_key = input.supabase_key || process.env.SUPABASE_KEY;
    
    if (!supabase_url || !supabase_key) {
        throw new Error('Supabase credentials required! Set SUPABASE_URL and SUPABASE_KEY in Environment variables or pass in input.');
    }
    
    log.info('Подключение к Supabase...');
    const supabase = createClient(supabase_url, supabase_key);
    
    // Получаем список reels для обработки
    log.info(`Получение списка reels (limit: ${batch_limit}, unanalyzed_only: ${filter_unanalyzed_only})...`);
    
    let query = supabase
        .from('reels')
        .select('id, source_video_url, storage_video_path, caption, hashtags, url, likes_count, comments_count, video_view_count, video_play_count')
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
        log.info('Нет reels для обработки');
        return;
    }
    
    log.info(`Найдено ${reels.length} reels для анализа`);
    
    // Обрабатываем каждый reel
    for (let i = 0; i < reels.length; i++) {
        const reel = reels[i];
        log.info(`\n[${i + 1}/${reels.length}] Обработка reel: ${reel.id}`);
        
        try {
            // Формируем video_url
            // Приоритет: Storage (более стабильный) → source_video_url (может истечь)
            let video_url;
            if (reel.storage_video_path) {
                video_url = `${supabase_url}/storage/v1/object/public/reels/${reel.storage_video_path}`;
                log.info(`Используем Storage URL`);
            } else if (reel.source_video_url) {
                video_url = reel.source_video_url;
                log.info(`Используем source URL (Storage отсутствует)`);
            } else {
                log.warning(`Reel ${reel.id} не имеет video_url, пропускаем`);
                continue;
            }
            
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
            
            // Сохраняем в Google Sheets (если настроено)
            if (input.google_sheets_id) {
                try {
                    await saveToGoogleSheets(input, reel, result, apiKey);
                } catch (error) {
                    log.warning(`Не удалось сохранить в Google Sheets: ${error.message}`);
                }
            }
            
            log.info(`✅ Reel ${reel.id} обработан успешно`);
            
        } catch (error) {
            log.error(`❌ Ошибка обработки reel ${reel.id}: ${error.message}`);
            // Продолжаем обработку следующих
        }
    }
    
    log.info(`\n🎉 Batch обработка завершена: ${reels.length} reels`);
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
    
    log.info(`Анализ рилса: ${reel_id}`);
    log.info(`Video URL: ${video_url}`);
    
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
    
    log.info('✅ Анализ завершён успешно!');
}

/**
 * Основная функция анализа рилса
 */
async function analyzeReel(params, apiKey) {
    const { reel_id, video_url, caption, hashtags, analysis_window_seconds, ocr_times } = params;
    
    // 1. Скачиваем видео
    log.info('Скачивание видео...');
    const videoPath = await downloadVideo(video_url);
    
    // 2. Извлекаем аудио
    log.info(`Извлечение аудио (${analysis_window_seconds}s)...`);
    const audioPath = await extractAudio(videoPath, analysis_window_seconds);
    
    // 3. ASR - распознавание речи
    log.info('ASR анализ...');
    const speechSegments = await transcribeAudio(audioPath, apiKey);
    log.info(`Распознано ${speechSegments.length} сегментов речи`);
    
    // 4. OCR - текст на экране
    log.info('OCR анализ...');
    const onscreenTextSegments = await analyzeOCR(videoPath, ocr_times, apiKey);
    log.info(`Извлечено ${onscreenTextSegments.length} текстовых сегментов`);
    
    // 5. Visual Events
    log.info('Анализ визуальных событий...');
    const visualEvents = await analyzeVisualEvents(videoPath, ocr_times, apiKey);
    log.info(`Обнаружено ${visualEvents.length} визуальных событий`);
    
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
        log.info('Результаты обновлены в Supabase');
    } else {
        await supabase
            .from('reel_analysis_raw')
            .insert(record);
        log.info('Результаты сохранены в Supabase');
    }
}

/**
 * Анализирует хук в первые 5 секунд видео
 */
async function analyzeHookType(caption, audioTranscript, screenText, visualEvents, apiKey) {
    // Формируем структурированный контекст
    const context = {
        transcript_first5: audioTranscript.substring(0, 500) || "",
        subtitles_first_lines: "",  // У нас нет субтитров отдельно
        caption_intro: caption.split('\n').slice(0, 2).join(' ').substring(0, 300) || "",
        ocr_text_first_frames: screenText.substring(0, 300) || "",
        visual_events: parseVisualEvents(visualEvents),
        language_hint: detectLanguage(caption, audioTranscript)
    };
    
    // Если вообще нет данных
    if (!audioTranscript && !screenText && !caption && !visualEvents) {
        return {
            hook_text: "No content available",
            channel: "VISUAL",
            hook_type: "OTHER",
            starts_with: "VISUAL_ONLY",
            strength: 1
        };
    }
    
    const prompt = `Ты — ассистент, который анализирует короткие вертикальные видео (Reels/Shorts/TikTok) и помогает найти главный "hook" в первых секундах ролика.

Определение "hook":
- это самое цепляющее событие в первые 5 секунд видео,
- которое должно остановить скролл и заставить зрителя продолжить смотреть,
- это может быть фраза, вопрос, визуальный приём, жёсткое обещание, шок, юмор, оффер и т.п.

Важно:
- Hook может быть НЕ только текстом / речью.
- Hook может быть чисто визуальным: привлекательная девушка/парень крупным планом; быстрые смены кадров; крупный текст на экране; сильная эмоция; демонстрация результата; крупный показ продукта; деньги/роскошь; необычный ракурс или действие.

Входные данные:
${JSON.stringify(context, null, 2)}

Твоя задача:
1. Проанализировать ВСЕ каналы: речь, субтитры, подпись, текст на экране, визуальные события.
2. Найти ОДИН главный хук — самый сильный и характерный.
3. Описать его КОРОТКОЙ фразой (не длиннее 160 символов).
4. Определить через какой канал реализован хук: VOICE, TEXT, VISUAL, MIX.
5. Определить тип хука и силу (1-10).

Верни СТРОГО один JSON-объект БЕЗ дополнительных комментариев:

{
  "hook_text": "строка с описанием главного хука",
  "channel": "VOICE | TEXT | VISUAL | MIX",
  "hook_type": "QUESTION | PAIN_POINT | BIG_PROMISE | PATTERN_INTERRUPT | STORY_PERSONAL | AUTHORITY_PROOF | HOW_TO | FOMO_URGENCY | VISUAL_SEX_APPEAL | VISUAL_MONEY_STATUS | RESULT_BEFORE_AFTER | OTHER",
  "starts_with": "QUESTION | NUMBER | STATEMENT | VISUAL_ONLY",
  "strength": 7
}`;

    try {
        const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: 'openai/gpt-4o-mini',
                messages: [{
                    role: 'user',
                    content: prompt
                }],
                temperature: 0.2,
                max_tokens: 300,
                response_format: { type: "json_object" }
            })
        });
        
        if (!response.ok) {
            log.warning(`Hook analysis error: ${response.status}`);
            return formatHookFallback(audioTranscript, screenText, visualEvents);
        }
        
        const data = await response.json();
        const hookData = JSON.parse(data.choices[0].message.content.trim());
        
        // Возвращаем объект для дальнейшей обработки
        return hookData;
        
    } catch (error) {
        log.warning(`Hook analysis exception: ${error.message}`);
        return formatHookFallback(audioTranscript, screenText, visualEvents);
    }
}

/**
 * Парсит визуальные события в нужный формат
 */
function parseVisualEvents(visualEventsString) {
    if (!visualEventsString) return [];
    
    const events = [];
    const parts = visualEventsString.split(';');
    
    for (const part of parts) {
        const match = part.trim().match(/^(\d+(?:\.\d+)?)s:(.+)$/);
        if (match) {
            const time = parseFloat(match[1]);
            const event = match[2].trim();
            
            // Мапим наши события в стандартные типы
            let eventType = 'OTHER';
            if (event.includes('FACE_CLOSEUP')) eventType = 'FACE_CLOSEUP';
            else if (event.includes('BIG_TEXT')) eventType = 'BIG_TEXT';
            else if (event.includes('LOGO') || event.includes('BRAND')) eventType = 'LOGO_OR_PRODUCT';
            else if (event.includes('SCENE_CHANGE')) eventType = 'QUICK_CUTS';
            
            events.push({
                time,
                event: eventType,
                description: event
            });
        }
    }
    
    return events;
}

/**
 * Определяет язык контента
 */
function detectLanguage(caption, transcript) {
    const text = (caption + ' ' + transcript).toLowerCase();
    
    if (/[а-яё]/.test(text)) return 'ru';
    if (/[a-z]/.test(text) && text.length > 20) {
        // Проверяем на индонезийские слова
        const indonesianWords = ['yang', 'ini', 'itu', 'untuk', 'dengan', 'dari', 'tidak', 'siapa', 'apa', 'kapan'];
        const hasIndonesian = indonesianWords.some(word => text.includes(word));
        if (hasIndonesian) return 'id';
        return 'en';
    }
    
    return null;
}

/**
 * Fallback если API не сработал
 */
function formatHookFallback(audioTranscript, screenText, visualEvents) {
    const hasQuestion = /\?/.test(audioTranscript + screenText);
    const hasFaceCloseup = /FACE_CLOSEUP/.test(visualEvents);
    const hasBigText = /BIG_TEXT/.test(visualEvents);
    
    let hookType = 'OTHER';
    let channel = 'MIX';
    let startsW = 'STATEMENT';
    let strength = 5;
    
    if (hasQuestion) {
        hookType = 'QUESTION';
        startsW = 'QUESTION';
        strength = 7;
    } else if (hasFaceCloseup) {
        hookType = 'VISUAL_SEX_APPEAL';
        channel = 'VISUAL';
        startsW = 'VISUAL_ONLY';
        strength = 6;
    } else if (hasBigText && screenText) {
        hookType = 'PATTERN_INTERRUPT';
        channel = 'TEXT';
        strength = 6;
    }
    
    const hookText = audioTranscript.substring(0, 100) || screenText.substring(0, 100) || 'Visual hook';
    
    return {
        hook_text: hookText,
        channel,
        hook_type: hookType,
        starts_with: startsW,
        strength
    };
}

/**
 * Сохраняет результаты в Google Sheets
 */
async function saveToGoogleSheets(input, reel, results, apiKey) {
    // Получаем credentials из input или Environment variables
    const google_service_account_json = input.google_service_account_json || process.env.GOOGLE_SERVICE_ACCOUNT_JSON;
    
    if (!google_service_account_json) {
        throw new Error('google_service_account_json is required for Google Sheets integration');
    }
    
    // Парсим Service Account JSON
    let credentials;
    try {
        credentials = typeof google_service_account_json === 'string'
            ? JSON.parse(google_service_account_json)
            : google_service_account_json;
    } catch (error) {
        throw new Error('Invalid google_service_account_json format');
    }
    
    // Инициализируем Google Sheets API
    const auth = new google.auth.GoogleAuth({
        credentials,
        scopes: ['https://www.googleapis.com/auth/spreadsheets']
    });
    
    const sheets = google.sheets({ version: 'v4', auth });
    
    // Формируем строку данных для анализа хуков
    const timestamp = new Date().toISOString();
    const caption = reel.caption || '';
    const audio_transcript = results.speech_segments.map(s => s.text).join(' ');  // Полная транскрипция
    const screen_text = results.onscreen_text_segments.map(s => s.text).join(' '); // Полный текст с экрана
    const visual_events = results.visual_events.map(e => `${e.time}s:${e.event}`).join('; ');
    
    // Анализируем тип хука
    log.info('Анализ типа хука...');
    const hook_analysis = await analyzeHookType(caption, audio_transcript, screen_text, visual_events, apiKey);
    
    // Форматируем результат для отображения
    let hook_display = 'Analysis Error';
    try {
        if (typeof hook_analysis === 'object') {
            hook_display = `[${hook_analysis.hook_type}] ${hook_analysis.channel} (${hook_analysis.strength}/10): ${hook_analysis.hook_text}`;
            log.info(`🎯 Хук: ${hook_analysis.hook_type} | Канал: ${hook_analysis.channel} | Сила: ${hook_analysis.strength}/10`);
            log.info(`   Текст: ${hook_analysis.hook_text.substring(0, 80)}...`);
        } else {
            hook_display = String(hook_analysis);
            log.info(`Тип хука: ${hook_display}`);
        }
    } catch (e) {
        hook_display = 'Format Error';
    }
    
    const row = [
        timestamp,                  // A: Timestamp
        reel.url || '',            // B: URL
        reel.id,                   // C: Reel ID
        reel.likes_count || 0,     // D: Likes
        reel.comments_count || 0,  // E: Comments
        reel.video_view_count || 0, // F: Views
        reel.video_play_count || 0, // G: Plays
        caption,                   // H: Caption (Original)
        '',                        // I: Caption (EN) - для ручного перевода
        audio_transcript,          // J: Audio Transcript (ID)
        '',                        // K: Audio Transcript (EN) - для ручного перевода
        screen_text,               // L: Screen Text (ID)
        '',                        // M: Screen Text (ENG) - для ручного перевода
        hook_display,              // N: Hook Type - автоматически с деталями!
        visual_events              // O: Visual Events
    ];
    
    // Добавляем строку в таблицу (используем первый лист)
    await sheets.spreadsheets.values.append({
        spreadsheetId: input.google_sheets_id,
        range: 'A:O',  // 15 столбцов: A-O
        valueInputOption: 'RAW',
        resource: {
            values: [row]
        }
    });
    
    log.info(`✅ Результаты сохранены в Google Sheets для reel ${reel.id}`);
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
            log.warning(`OCR error at ${time}s: ${error.message}`);
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
            log.warning(`Frame error at ${time}s: ${error.message}`);
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
            log.warning(`Cleanup error: ${error.message}`);
        }
    }
}

