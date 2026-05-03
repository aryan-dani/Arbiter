# Implementation Plan: CRUD Operations & Scan/Commit History on Frontend

To fulfill the requirement of having full CRUD (Create, Read, Update, Delete) operations for scans, and displaying the detailed commit history on the frontend, we need to extend both the backend API and the React frontend. 

Here is the step-by-step walkthrough and implementation plan.

---

## 1. Backend Enhancements (FastAPI + PostgreSQL)

Currently, Arbiter's backend supports **Create** (`POST /start-healing`) and **Read** (`GET /api/runs` and `GET /api/runs/{run_id}`). We need to introduce **Update** and **Delete** functionalities.

### A. Update `backend/utils/db_manager.py`
We need to add two new methods to the database manager:
- `delete_run(self, run_id: str)`: Executes a `DELETE FROM agent_runs WHERE id = %s`. (Because of the `ON DELETE CASCADE` constraint on `node_logs`, this will also safely wipe the associated logs).
- `update_run(self, run_id: str, team_name: str)`: Executes an `UPDATE agent_runs SET team_name = %s WHERE id = %s` to allow users to rename or edit the run metadata.

### B. Update `backend/main.py`
We must expose these new database methods as REST API endpoints:
- **DELETE** `DELETE /api/runs/{run_id}`: Calls the `delete_run` method and returns a success status.
- **UPDATE**: `PUT /api/runs/{run_id}`: Calls the `update_run` method to modify the team name/run name.
*(Note: The commit history is already successfully tracked in the DB and exposed via `GET /api/runs/{run_id}/logs`.)*

---

## 2. Frontend Enhancements (React + Vite)

The frontend currently features a `DashboardPage.jsx` that lists runs but lacks deletion, updating, and an expanded view to see the actual commit history.

### A. Add "Update" and "Delete" to `DashboardPage.jsx`
- **Delete functionality:** Add a "Trash" icon button to each scan card. Clicking it will trigger the `DELETE /api/runs/{id}` endpoint and remove the scan from the UI.
- **Update functionality:** Add an "Edit" icon button that opens a small prompt or modal allowing the user to rename the scan/team name. It will trigger the `PUT /api/runs/{id}` endpoint.

### B. Create a Detailed View for Commit History
Currently, you can see the *result* of the scan, but not the *steps* it took. 
- Create a new component: `src/pages/RunDetailsPage.jsx`.
- Update your router (in `main.jsx` or `App.jsx`) to include a new route: `/run/:id`.
- Make the cards in `DashboardPage.jsx` clickable to route the user to `/run/:id`.

### C. Visualize the Commit History
Inside `RunDetailsPage.jsx`:
1. Fetch the run metadata via `GET /api/runs/{id}`.
2. Fetch the timeline via `GET /api/runs/{id}/logs`.
3. Filter the logs to specifically find items where `log_type === 'FIX_APPLIED'`. 
4. Render these logs in a vertical timeline UI. Since each `FIX_APPLIED` log contains the `commit_message`, `bug_type`, and the actual code diffs, we can render a beautiful "Commit History" section showing exactly what lines of code the AI agent modified for that specific scan.

---

## 3. Execution

If you approve this plan, I can immediately start implementing these changes by modifying `db_manager.py`, `main.py`, and building out the new React components!
