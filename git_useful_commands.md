# Activate virtual environment 
On Windows, use: envName\Scripts\activate 
On Windows (git bash terminal): source ./envName/Scripts/activate
On macOS and Linux, use: source ./envName/bin/activate 


# ================================
# Getting App to run on a new PC
# ================================
1) Clone Repo
2) Switch to a branch other than main/master
3) Create virtual environment: python -m venv [environment_name]
4) Activate virtual environment created in step 3 (in windows envName\Scripts\activate & on linux source ./envName/bin/activate)
5) Installed required packages: pip install -r requirements.txt
6) Run the tool: python analyze_trades.py

# ============
# GIT Tips
# ============
# Ignore local changes and reset to one of the previous commits:
1) We can list of commits with: git log --oneline
2) And then reset our local branch to a commit with: git reset --hard 91dbf83
3) If there were any new files added, we can clean them up with: git clean -fd

# Make main same as development & push changes to remote
1) checkout main: git checkout main
2) merge: git merge --ff-only development
if merge fails, force rest: git reset --hard development
If development is only on remote (i.e. not checked in to local computer), then: git reset --hard origin/development
3) push changes to remote: git push origin main --force

# Discard all remote changes and make remote branch same as the local branch
git push origin <branch_name> --force

# Discard all local changes and make your branch identical to the remote branch, follow these steps:
1) git fetch origin
2) git reset --hard origin/branch-name
3) git clean -fd

# Create a new branch from the current and push to remote
1) create a new branch: git checkout -b new-branch-name
2) push to remote: git push --set-upstream origin new-branch-name

# Delete both local and remote branch
git push origin --delete branch_name      # deletes remote branch
git branch -d branch_name                 # or -D to force delete, deletes local branch

# See name of the repo
git remote -v