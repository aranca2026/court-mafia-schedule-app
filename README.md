# Tournament Schedule Web App

This package converts your Excel-based tournament schedule into a shareable Streamlit web app.

## What is included
- `app.py` – main Streamlit app
- `data_loader.py` – Excel parsing, cleaning, player search, leaderboard logic
- `tournament_schedule.xlsx` – your current workbook, bundled as the default data source
- `requirements.txt` – dependencies
- `README.md` – deployment steps

## Features included
1. Full tournament schedule dashboard
2. Category / court / status filters
3. Court-wise fixture view
4. Player search
5. Leaderboard generated from score columns in the workbook
6. CSV export for filtered fixtures

## Folder structure
```text
tournament_web_app/
├── app.py
├── data_loader.py
├── requirements.txt
├── README.md
└── tournament_schedule.xlsx
```

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publish on Streamlit Community Cloud
1. Create a GitHub repository and upload all files from this folder.
2. Go to Streamlit Community Cloud and sign in with GitHub.
3. Click **Create app**.
4. Select your repository, branch, and set the main file path to `app.py`.
5. Deploy.
6. Share the generated public link with players or convert it into a QR code for the venue.

## Fast 10-minute publish workflow
### Route A – simplest
- Upload this folder to a new GitHub repo
- Deploy on Streamlit Community Cloud
- Share the app URL

### Route B – with branding
- Add your tournament logo to the repo
- Update `st.title()` and colours in `app.py`
- Re-deploy

## Data expectations
The app relies mainly on the `Schedule` sheet.
For best results, keep these columns available:
- Category
- Venue
- Start Time
- End Time
- Round Name
- Court No
- Match Details
- Team 1 Name / Team 2 Name
- Team 1 Score / Team 2 Score

## Notes
- The leaderboard is computed from score columns in the workbook.
- If your Excel uses placeholder scores before matches are played, update those scores in Excel and re-upload the workbook for accurate standings.
- You can replace `tournament_schedule.xlsx` with future editions of the tournament workbook as long as the same core sheet structure is maintained.
