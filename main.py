# main.py
from flow import create_codecredx_flow
import json
import sys
import os

def main():
    """
    Main function to run the CodeCredX application.
    It initializes the flow, runs it, and prints the results.
    The 'shared' dictionary is expected to be modified in-place by PocketFlow.
    """
    print("Starting CodeCredX application...")

    # Initialize a shared dictionary.
    # This dictionary will be used by nodes to pass data between them.
    shared = {
        "resume_text": None,            # To store the raw resume content
        "github_project_urls": [],      # To store extracted GitHub project URLs
        "other_urls": [],               # To store other non-GitHub URLs
        "analyzed_github_projects": []  # To store the detailed analysis of GitHub projects, including summaries
    }

    print(f"DEBUG: Initial shared dictionary ID: {id(shared)}")
    print("DEBUG: Initial shared dictionary content:")
    print(json.dumps(shared, indent=2))

    # Create the CodeCredX flow
    codecredx_flow = create_codecredx_flow()

    # Run the flow with the shared dictionary
    # The nodes will populate the shared dictionary with their results in-place.
    print("\n--- Running CodeCredX Flow ---")
    try:
        # We explicitly ignore the return value of flow.run()
        # as PocketFlow modifies the 'shared' dictionary in-place.
        codecredx_flow.run(shared)
        print("DEBUG: Flow.run completed. Assuming 'shared' dictionary was modified in-place.")

    except Exception as e:
        print(f"\nCRITICAL ERROR: An unhandled exception occurred during flow execution: {e}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f"Error Type: {exc_type}, File: {fname}, Line: {exc_tb.tb_lineno}")
        import traceback
        traceback.print_exc() # Print full traceback
        print("Flow terminated prematurely.")


    # --- Print the results from the shared dictionary ---
    print("\n--- CodeCredX Flow Execution Complete ---")
    print(f"DEBUG: Final shared dictionary ID: {id(shared)}") # Should be the same as initial ID

    # Now, 'shared' should reliably be a dictionary with updated contents
    print("\nExtracted GitHub Project URLs:")
    if shared.get("github_project_urls"): # Use .get for safer access
        for url in shared["github_project_urls"]:
            print(f"- {url}")
    else:
        print("No GitHub project URLs found.")

    print("\nExtracted Other URLs:")
    if shared.get("other_urls"): # Use .get for safer access
        for url in shared["other_urls"]:
            print(f"- {url}")
    else:
        print("No other URLs found.")

    print("\nAnalyzed GitHub Projects (with Summaries):")
    if shared.get("analyzed_github_projects"): # Use .get for safer access
        for project in shared["analyzed_github_projects"]:
            print(f"\n--- Project: {project['url']} ---")
            print(f"  Status: {project['status']}")
            if project.get('error'):
                print(f"  Error: {project['error']}")
            print("  Metadata:")
            for key, value in project['metadata'].items():
                if key == "description" and value:
                    print(f"    {key}: {value[:70]}..." if len(value) > 70 else f"    {key}: {value}")
                else:
                    print(f"    {key}: {value}")
            if project.get('readme_content'):
                print(f"  README Content (first 100 chars):\n    {project['readme_content'][:100]}...")
            else:
                print("  README Content: Not available or failed to fetch.")
            print(f"  LLM Summary: {project.get('summary')}")
    else:
        print("No GitHub projects analyzed.")

    print("\n--- Full Shared Dictionary State After Flow ---")
    print(json.dumps(shared, indent=2))

if __name__ == "__main__":
    main()
