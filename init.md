# Task:

Build a job search assistant that

1. analyze experience:
2. crawls postings from major tech companies and linkedin, analyzes them to find matches
3. analyze the company to find the culture, vision and tech match
4. tailor the resume and cv based on the job description and my real expeirence to apply the job
5. based on the company reviews to prepar for the interviews

## Workflow plan
1. Self Preparation

Current experience Summary -> Extract Key Achievements and Abilities -> build project story telling -> Matching to common asked questions -> Generate Candidate Profile, Resume, Preference and Skill sets

2. Job Hunting

 Job boards / company career pages / user-provided links
                         |
                 Authorized connectors
                         |
             Ingestion, parsing, deduplication
                         |
        +----------------+----------------+
        |                                 |
   Job database                    Candidate profile
        |                           Resume, skills,
        |                           preferences, history
        +----------------+----------------+
                         |
                 Match and rank jobs
                         |
                  Job-search workspace
            Review, save, reject, or pursue
                         |
               Application preparation
       Tailored resume + cover letter + answers
                         |
                  User approval gate
                         |
           Application submission or handoff
                         |
       Interview briefings, practice, follow-up
       
## Examples:

- https://github.com/gilgameshcc/ai-native-jobhunt/tree/main (most similar)
- https://github.com/he-yufeng/FindJobs-Agent#features
- https://github.com/kaymen99/Upwork-AI-jobs-applier

# Development

Tech stack adoptions: 
- backend: Python + FastAPI 
- API and background worker: GCP Cloud Run
- Data Storage: GCP Cloud storage (not decided yet)
- Development Kit: VSCode + Cline
- Model Selection: OpenRouter
- Observability: OpenTelemetry + Grafana for observability (potentially using Langfuse for evaluation or trace inspection)