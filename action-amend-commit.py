# When this action is run, it will check if the last commit is made by
# github-actions[bot] <github-actions[bot]@users.noreply.github.com>.
# If it is, it will amend the last commit with the new changes and force push it.
# Otherwise, it will create a new commit with the changes.

import subprocess
import sys

def get_last_commit_author():
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%ae"],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()

def amend_last_commit():
    try:
        # Only add commits of modified files
        subprocess.run(
            ["git", "add", "-A"],
            check=True
        )
        subprocess.run(
            ["git", "commit", "--amend", "--no-edit"],
            check=True
        )
        subprocess.run(
            ["git", "push", "--force-with-lease"],
            check=True
        )
        print("Last commit amended and pushed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error amending last commit: {e}", file=sys.stderr)
        sys.exit(1)

def create_new_commit():
    try:
        subprocess.run(
            ["git", "commit", "-a", "-m", "Update Profile [skip ci]"],
            check=True
        )
        subprocess.run(
            ["git", "push"],
            check=True
        )
        print("New commit created and pushed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating new commit: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    last_commit_author = get_last_commit_author()
    if last_commit_author == "github-actions[bot]@users.noreply.github.com":
        amend_last_commit()
    else:
        create_new_commit()

if __name__ == "__main__":
    exit(main())
