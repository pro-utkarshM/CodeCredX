# main.py
import logging
import sys
import os
import json
from flow import create_codecredx_flow
from config import app_config

def setup_logging():
    """
    Sets up the logging configuration for the application.
    Logs to both console and a file.
    """
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file_path = os.path.join(log_dir, app_config.LOG_FILE)

    logging.basicConfig(
        level=app_config.LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured. Log level: {app_config.LOG_LEVEL}, Log file: {log_file_path}")
    return logger


def main():
    logger = setup_logging()

    logger.info("Starting CodeCredX application...")

    # Determine the resume file path from command-line arguments
    resume_file_path = None
    if len(sys.argv) > 1:
        resume_file_path = sys.argv[1]
        logger.info(f"Resume file path provided via command line: {resume_file_path}")
    else:
        logger.warning("No resume file path provided via command line. The ResumeInputNode will use its default simulated content.")

    shared = {
        "resume_text": None,
        "github_project_urls": [],
        "other_urls": [],
        "analyzed_github_projects": [],
        "overall_candidate_metrics": {},
        "candidate_report": None,
        "resume_file_path": resume_file_path # NEW: Add file_path to shared dictionary
    }

    logger.debug(f"Initial shared dictionary ID: {id(shared)}")
    logger.debug(f"Initial shared dictionary content:\n{json.dumps(shared, indent=2)}")

    codecredx_flow = create_codecredx_flow()

    logger.info("\n--- Running CodeCredX Flow ---")
    try:
        # Now call flow.run without the file_path keyword argument.
        # ResumeInputNode will pick it up from 'shared'.
        codecredx_flow.run(shared)
        logger.info("Flow.run completed. 'shared' dictionary was modified in-place.")

    except Exception as e:
        logger.critical(f"An unhandled exception occurred during flow execution: {e}", exc_info=True)
        logger.error("Flow terminated prematurely.")

    logger.info("\n--- CodeCredX Flow Execution Complete ---")
    logger.debug(f"Final shared dictionary ID: {id(shared)}")

    logger.info("\nExtracted GitHub Project URLs:")
    if shared.get("github_project_urls"):
        for url in shared["github_project_urls"]:
            logger.info(f"- {url}")
    else:
        logger.info("No GitHub project URLs found.")

    logger.info("\nExtracted Other URLs:")
    if shared.get("other_urls"):
        for url in shared["other_urls"]:
            logger.info(f"- {url}")
    else:
        logger.info("No other URLs found.")

    logger.info("\nAnalyzed GitHub Projects (with Summaries and Scores):")
    if shared.get("analyzed_github_projects"):
        for project in shared["analyzed_github_projects"]:
            logger.info(f"\n--- Project: {project['url']} ---")
            logger.info(f"  Status: {project['status']}")
            if project.get('error'):
                logger.error(f"  Error: {project['error']}")
            logger.info("  Metadata:")
            for key, value in project['metadata'].items():
                if key == "description" and value:
                    logger.info(f"    {key}: {value[:70]}..." if len(value) > 70 else f"    {key}: {value}")
                else:
                    logger.info(f"    {key}: {value}")
            if project.get('readme_content'):
                logger.info(f"  README Content (first 100 chars):\n    {project['readme_content'][:100]}...")
            else:
                logger.info("  README Content: Not available or failed to fetch.")
            logger.info(f"  LLM Summary: {project.get('summary')}")
            logger.info("  Scores:") # This line is correctly indented
            if project.get("scores"): # This line was incorrectly indented
                for score_name, score_value in project["scores"].items():
                    logger.info(f"    {score_name}: {score_value}")
            else:
                logger.info("    No scores assigned.")
    else:
        logger.info("No GitHub projects analyzed.")

    logger.info("\n--- Overall Candidate Metrics ---")
    if shared.get("overall_candidate_metrics"):
        for metric_name, metric_value in shared["overall_candidate_metrics"].items():
            logger.info(f"  {metric_name}: {metric_value}")
    else:
        logger.info("No overall candidate metrics found.")

    logger.info("\n--- Candidate Report Status ---")
    if shared.get("candidate_report"):
        logger.info("Candidate report generated and saved to 'logs/candidate_report.md'.")
    else:
        logger.warning("Candidate report was not generated.")

    logger.debug("\n--- Full Shared Dictionary State After Flow ---")
    logger.debug(json.dumps(shared, indent=2))
    logger.info("CodeCredX application finished.")

if __name__ == "__main__":
    main()
