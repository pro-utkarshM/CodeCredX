from flow import create_flow

def main():
    shared = {}
    flow = create_flow()
    flow.run(shared)
    print("\n--- Final Shared Object ---")
    for key, value in shared.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()
