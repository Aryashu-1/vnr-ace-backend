import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_portal():
    print("Testing Application Portal Endpoints...")
    
    # 1. Get Jobs
    print("\n1. Fetching Job Listings...")
    response = requests.get(f"{BASE_URL}/placements/jobs")
    if response.status_code == 200:
        jobs = response.json()
        print(f"Success: Found {len(jobs)} jobs")
        if jobs:
            job_id = jobs[0]['id']
            print(f"Sample Job: {jobs[0]['role']} at {jobs[0]['company_name']} (ID: {job_id})")
            
            # 2. Get Job Detail
            print(f"\n2. Fetching Detail for Job {job_id}...")
            detail_res = requests.get(f"{BASE_URL}/placements/jobs/{job_id}")
            if detail_res.status_code == 200:
                print(f"Success: {detail_res.json()['role']} details fetched")
            else:
                print(f"Failed to fetch job detail: {detail_res.status_code}")
        else:
            print("No jobs found in DB. Run populate_jobs.py first.")
    else:
        print(f"Failed to fetch jobs: {response.status_code}")

    # 3. Get My Applications
    print("\n3. Fetching My Applications...")
    response = requests.get(f"{BASE_URL}/placements/my-applications")
    if response.status_code == 200:
        apps = response.json()
        print(f"Success: Found {len(apps)} applications")
    else:
        print(f"Failed (expected if no auth): {response.status_code}")

    # 4. Get Policies
    print("\n4. Fetching Policies...")
    response = requests.get(f"{BASE_URL}/placements/policies")
    if response.status_code == 200:
        print("Success: Policies fetched")
    else:
        print(f"Failed: {response.status_code}")

if __name__ == "__main__":
    test_portal()
