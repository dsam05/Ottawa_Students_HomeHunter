# Ottawa_Students_HomeHunter

Local web app for importing Realtor.ca URLs and sorting listings by school proximity, safety, and price.

The project name is **Ottawa_Students_HomeHunter**. The app name shown in the UI is **Ottawa Student's HomeHunter**.

Imports look for both OCDSB public and OCSB Catholic schools by default. School-board choice lives in the filters as a checkbox dropdown.

For first-time setup instructions, read [install.md](install.md). For the product walkthrough and design story, read [documentation.md](documentation.md). For architecture, data model, API details, project tree, and extension notes, read [technical_documentation.md](technical_documentation.md).

## Screenshots

Representative app screenshots are kept in [screenshots](screenshots):

- [Home dashboard](screenshots/01-home-dashboard.png)
- [Filter panel](screenshots/02-filter-panel.png)
- [Proximity slider](screenshots/03-proximity-slider.png)
- [Condo fee slider](screenshots/04-condo-fee-slider.png)
- [Listing cards with blurred headers](screenshots/05-listing-cards-headers-blurred.png)
- [Listing detail area with blurred headers](screenshots/06-listing-card-detail-headers-blurred.png)
- [School-board filter dropdown](screenshots/07-school-board-filter-dropdown.png)

## Run

Use the script for your platform:

```bash
./app_run_scripts/macos/start_app.sh
./app_run_scripts/linux/start_app.sh
```

Windows PowerShell:

```powershell
.\app_run_scripts\windows\start_app.ps1
```

Open `http://127.0.0.1:5001`.

Stop the app with the matching stop script in the same platform folder.

## Development

Development setup, project structure, test commands, Git hygiene, API details, and extension notes are documented in [technical_documentation.md](technical_documentation.md).
