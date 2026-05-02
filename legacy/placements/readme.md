# Resume Utilities Guide

This folder contains the resume ingestion and resume evaluation helpers used for placement workflows.

## What each file does

- `resume_ingester.py`  
  Reads all PDF resumes from the `resumes/` folder, chunks the text, generates embeddings, and builds a FAISS index.

- `resumes.py`  
  Contains:
  - `ResumeShortlister` — ranks the most relevant resumes for a job description using the FAISS index.
  - `ResumeAdvisor` — reviews a single resume and gives ATS/recruiter-style feedback using Gemini.

---

## Prerequisites

Use Python `3.11` and install the required packages.

### Core packages

```bash
pip install pdfplumber python-docx google-generativeai faiss-cpu sentence-transformers pymupdf spacy numpy python-dotenv pydantic
```

### spaCy model

```bash
python -m spacy download en_core_web_sm
```

> If you are using Poetry, run the same commands inside the project environment with `poetry run`.

---

## Recommended folder structure

Make sure the `placements/` folder looks like this:

```text
placements/
├── readme.md
├── resume_ingester.py
├── resumes.py
├── resumes/                 # add all resume files here
│   ├── student1.pdf
│   ├── student2.pdf
│   └── ...
└── faiss_index/             # created after running the ingester
```

---

## Step 1: Add all resumes

Create a folder named `resumes` inside `placements/` and place all resume files there.

```bash
cd placements
mkdir -p resumes
```

> `resume_ingester.py` currently ingests only `.pdf` files.

---

## Step 2: Run the ingester

From inside the `placements/` directory, run:

```bash
cd placements
python resume_ingester.py
```

or with Poetry:

```bash
cd placements
poetry run python resume_ingester.py
```

This will:

1. Read all PDFs from `resumes/`
2. Extract and clean the text
3. Generate embeddings using `sentence-transformers/all-MiniLM-L6-v2`
4. Create:
   - `faiss_index/index.faiss`
   - `faiss_index/metadata.pkl`

Once this step is complete, you can use `ResumeShortlister`.

---

## Step 3: Run `ResumeShortlister`

`ResumeShortlister` **depends on the FAISS index created in Step 2**. Do not run it before the ingester has finished.

### Example usage

```python
from resumes import ResumeShortlister

shortlister = ResumeShortlister()

matches = shortlister.run(
    company_id="demo_company",
    job_description="Looking for a backend engineer with Python, FastAPI, REST APIs, SQL, and problem-solving skills.",
    top_k=5,
)

for resume_id, chunks in matches:
    best_score = max(chunk["score"] for chunk in chunks)
    print(resume_id, best_score)
```

### What it returns

It returns the top matching resumes ranked by similarity score.

---

## Run `ResumeAdvisor` independently

`ResumeAdvisor` can be used **without** running the ingester or FAISS pipeline.

It only needs a valid Gemini API key.

### Step A: Configure Gemini API key

Create a `.env` file in the project root (or export the variable in your shell):

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step B: Use `ResumeAdvisor`

```python
from resumes import ResumeAdvisor

advisor = ResumeAdvisor(
    name="Recruiter",
    email="recruiter@example.com"
)

advisor.review_resume("resumes/sample_resume.pdf")
```

### Supported file formats

- `.pdf`
- `.docx`
- `.txt`

---

## Important notes / gaps to keep in mind

- Run commands from inside the `placements/` folder because paths like `resumes/` and `faiss_index/` are currently relative.
- If you add or replace resumes later, rerun `resume_ingester.py` to rebuild the index.
- `ResumeShortlister` is for matching resumes against job descriptions.
- `ResumeAdvisor` is for detailed feedback on a single resume.
- Gemini access is required only for `ResumeAdvisor`.

---

## Quick workflow summary

1. Create `placements/resumes/` and add all resume PDFs.
2. Run `python resume_ingester.py` from inside `placements/`.
3. After the index is created, use `ResumeShortlister`.
4. `ResumeAdvisor` can be run independently once `GEMINI_API_KEY` is configured.
