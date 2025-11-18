"""Main CLI entry point for Instagram Reels Analysis Pipeline."""
import argparse
import sys
from pathlib import Path

from services.ingestion import ingest_apify_json
from services.downloader import download_all_pending_videos
from services.analyzer import analyze_all_pending_reels
from services.analyzer_hooks import classify_all_pending_hooks
from services.scoring import update_all_scores
from services.parallel import (
    process_downloads_parallel,
    process_analysis_parallel,
    process_hooks_parallel,
)
from services.progress import print_download_progress


def cmd_ingest(args):
    """Команда импорта JSON от Apify."""
    json_path = Path(args.json)
    
    if not json_path.exists():
        print(f"Error: File {json_path} not found", file=sys.stderr)
        sys.exit(1)
    
    print(f"Ingesting reels from {json_path}...")
    
    try:
        reel_ids = ingest_apify_json(str(json_path))
        print(f"Successfully ingested {len(reel_ids)} reels")
    except Exception as e:
        print(f"Error during ingestion: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_download_videos(args):
    """Команда скачивания видео."""
    print("Downloading videos for all pending reels...")
    
    try:
        if args.parallel:
            process_downloads_parallel(max_workers=args.workers)
        else:
            download_all_pending_videos()
        print("Video download completed")
    except Exception as e:
        print(f"Error during video download: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_analyze_raw(args):
    """Команда анализа текста (ASR + OCR)."""
    print("Analyzing raw text for all pending reels...")
    
    try:
        if args.parallel:
            process_analysis_parallel(max_workers=args.workers)
        else:
            analyze_all_pending_reels()
        print("Raw analysis completed")
    except Exception as e:
        print(f"Error during raw analysis: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_classify_hooks(args):
    """Команда классификации хуков через LLM."""
    print("Classifying hooks for all pending reels...")
    
    try:
        if args.parallel:
            process_hooks_parallel(max_workers=args.workers)
        else:
            classify_all_pending_hooks()
        print("Hook classification completed")
    except Exception as e:
        print(f"Error during hook classification: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_update_scores(args):
    """Команда обновления метрик и скоринга."""
    print("Updating scores for all reels...")
    
    try:
        update_all_scores()
        print("Score update completed")
    except Exception as e:
        print(f"Error during score update: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Instagram Reels Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Команда ingest
    ingest_parser = subparsers.add_parser("ingest", help="Import JSON from Apify")
    ingest_parser.add_argument("--json", required=True, help="Path to Apify JSON file")
    ingest_parser.set_defaults(func=cmd_ingest)
    
    # Команда download-videos
    download_parser = subparsers.add_parser("download-videos", help="Download videos for pending reels")
    download_parser.add_argument("--parallel", action="store_true", help="Use parallel processing")
    download_parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers (default: 4)")
    download_parser.set_defaults(func=cmd_download_videos)
    
    # Команда analyze-raw
    analyze_parser = subparsers.add_parser("analyze-raw", help="Extract text (ASR + OCR) for pending reels")
    analyze_parser.add_argument("--parallel", action="store_true", help="Use parallel processing")
    analyze_parser.add_argument("--workers", type=int, default=2, help="Number of parallel workers (default: 2)")
    analyze_parser.set_defaults(func=cmd_analyze_raw)
    
    # Команда classify-hooks
    classify_parser = subparsers.add_parser("classify-hooks", help="Classify hooks via LLM for pending reels")
    classify_parser.add_argument("--parallel", action="store_true", help="Use parallel processing")
    classify_parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers (default: 4)")
    classify_parser.set_defaults(func=cmd_classify_hooks)
    
    # Команда update-scores
    scores_parser = subparsers.add_parser("update-scores", help="Update engagement rates and hook scores")
    scores_parser.set_defaults(func=cmd_update_scores)
    
    # Команда check-progress
    progress_parser = subparsers.add_parser("check-progress", help="Check download progress")
    progress_parser.set_defaults(func=lambda args: print_download_progress())
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()

