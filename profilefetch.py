#!/usr/bin/env python3
"""
GitHub Profile SVG Generator
Generates neofetch-style profile SVGs with statistics fetched from GitHub GraphQL API.
"""

import argparse
import os
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone

import requests

# SVG Configuration Constants
SVG_WIDTH = 1024
SVG_HEIGHT = None  # Will be calculated dynamically based on content
ASCII_HEIGHT = 258  # Height of ASCII art section, modify based on the art added

# GitHub language colors (subset - add more as needed)
LANGUAGE_COLORS = {
    'Python': '#3572A5',
    'JavaScript': '#f1e05a',
    'TypeScript': '#2b7489',
    'Java': '#b07219',
    'C++': '#f34b7d',
    'C': '#555555',
    'C#': '#239120',
    'Go': '#00ADD8',
    'Rust': '#dea584',
    'Ruby': '#701516',
    'PHP': '#4F5D95',
    'Swift': '#ffac45',
    'Kotlin': '#F18E33',
    'Scala': '#c22d40',
    'HTML': '#e34c26',
    'CSS': '#1572B6',
    'Shell': '#89e051',
    'Dockerfile': '#384d54',
    'YAML': '#cb171e',
    'JSON': '#292929',
    'Markdown': '#083fa1',
    'Vue': '#2c3e50',
    'React': '#61dafb',
    'Jupyter Notebook': '#DA5B0B',
    'R': '#198CE7',
    'MATLAB': '#e16737',
    'Objective-C': '#438eff',
    'Perl': '#0298c3',
    'Lua': '#000080',
    'Dart': '#00B4AB',
    'Haskell': '#5e5086',
    'Clojure': '#db5855',
    'Elixir': '#6e4a7e',
    'Erlang': '#B83998',
    'F#': '#b845fc',
    'OCaml': '#3be133',
    'PowerShell': '#012456',
    'Assembly': '#6E4C13',
    'Vim script': '#199f4b',
    'Makefile': '#427819',
    'CMake': '#DA3434',
    'Batchfile': '#C1F12E',
    'TeX': '#3D6117',
    'Groovy': '#e69f56',
    'ActionScript': '#882B0F',
    'CoffeeScript': '#244776',
    'LiveScript': '#499886',
    'PureScript': '#1D222D',
    'Elm': '#60B5CC',
    'Crystal': '#000100',
    'Nim': '#ffc200',
    'D': '#ba595e',
    'Zig': '#ec915c',
    'V': '#4f87c4',
    'Julia': '#a270ba',
    'Chapel': '#8dc63f',
    'Pike': '#005390',
    'Nix': '#7e7eff',
    'Racket': '#3c5caa',
    'Standard ML': '#dc566d',
    'Smalltalk': '#596706',
    'Ada': '#02f88c',
    'Fortran': '#4d41b1',
    'COBOL': '#005590'
}


def get_profile_content_definition(user_data):
    """
    Define the content structure for the profile.

    This function returns a list of tuples defining the content lines to display.
    Each tuple contains (key, value) where:
    - key: The field name or special marker
    - value: The field value or empty string for special cases

    Special markers:
    - "GAP": Adds vertical spacing
    - Keys starting with "—": Section headers
    - "PLACEHOLDER": Will be replaced with actual data during rendering
    - "BIO_OVERFLOW": Additional lines for bio overflow content (can be multiple lines)

    Args:
        user_data: GitHub user data from API

    Returns:
        List of (key, value) tuples defining the profile content
    """
    # Calculate age for uptime
    created_date = datetime.fromisoformat(user_data['createdAt'].replace('Z', '+00:00'))
    age = datetime.now(created_date.tzinfo) - created_date
    years = age.days // 365
    months = (age.days % 365) // 30
    days = (age.days % 365) % 30

    # Build the content structure
    content_lines = []

    # Bio section with special formatting
    bio_text = user_data.get("bio", "") or ""
    content_lines.append(("Bio", "We are not given a short life but we make it short, and we are not ill-supplied but wasteful of it. You know how important your time is, yet you ignore its passage and engage in low-value activities that pull you away from the things that really matter."))
    # BIO_OVERFLOW will be added dynamically during rendering if needed (can be multiple lines)

    # System info section
    content_lines.extend([
        ("Uptime", f"{years} years, {months} months, {days} days"),
        ("OS", "macOS"),
        ("Editors", "Cursor, Doom Emacs"),
    ])

    # Add gap before languages section
    content_lines.append(("GAP", ""))

    # Languages section
    content_lines.extend([
        ("Languages.Programming", "Typescript, Python, Haskell, Shell"),
        ("Languages.Markup", "Org-mode, Markdown, LaTeX"),
        ("Languages.Real", "English, Chinese"),
    ])

    # Add gap and Contact section header
    content_lines.extend([
        ("GAP", ""),
        ("— Contact ", ""),
    ])

    # Contact info
    content_lines.extend([
        ("Email.Contact", "hi@trine.dev"),
        ("Discord", "dotindiscorg"),
    ])

    # Add gap and GitHub Statistics section header
    content_lines.extend([
        ("GAP", ""),
        ("— GitHub Statistics ", ""),
    ])

    # GitHub Statistics (values will be replaced during rendering)
    content_lines.extend([
        ("Repository", "PLACEHOLDER"),  # repos, contributed repos, stars, followers
        ("Commits", "PLACEHOLDER"),  # commits, code line changes
        ("Issues", "PLACEHOLDER"),  # open/closed issues
        ("Pull Requests", "PLACEHOLDER")  # open/draft/merged/closed PRs
    ])

    return content_lines


def clean_and_visible_length(text):
    """Clean text of invisible characters and return the visible length"""
    if not text:
        return text, 0

    # Remove or normalize invisible characters
    cleaned = ''
    for char in text:
        # Skip zero-width characters and other invisible characters
        if unicodedata.category(char) in ['Cf', 'Mn', 'Me']:  # Format chars, nonspacing marks, enclosing marks
            continue
        # Skip specific invisible characters
        if char in ['\u200b', '\u200c', '\u200d', '\u2060', '\ufeff', '\u202a', '\u202b', '\u202c', '\u202d',
                    '\u202e']:
            continue
        cleaned += char

    # Calculate visual width (some characters may be wider)
    visual_length = 0
    for char in cleaned:
        # Most characters are width 1, but some CJK characters might be width 2
        if unicodedata.east_asian_width(char) in ['F', 'W']:  # Fullwidth or Wide
            visual_length += 2
        else:
            visual_length += 1

    return cleaned, visual_length


def get_text_length_without_tags(text):
    """Calculate the text length without XML/HTML tags"""
    # Remove all XML/HTML tags to get the actual text length
    clean_text = re.sub(r'<[^>]+>', '', text)
    return len(clean_text)


def format_bio_line(bio_text, total_width=75, max_lines=5, overflow_line_width=None):
    """
    Format bio line with special requirements:
    1. At least 8 dots
    2. Respect 75 character width limit for first line
    3. If overflow, create multiple left-aligned lines (up to max_lines total)
    4. Never break words - always break at word boundaries
    5. Lines 2-5 align with the start of line 2 (left-aligned)
    
    Args:
        bio_text: The bio text to format
        total_width: Width for first line (default 75)
        max_lines: Maximum total lines (default 5)
        overflow_line_width: Width for overflow lines (if None, calculated from SVG dimensions)

    Returns: (first_line_formatted, overflow_lines_list)
    """
    if not bio_text:
        bio_text = ""

    key_part = ". Bio:"
    min_dots = 8

    # Calculate overflow line width if not provided
    # Overflow lines start from bio_text_start_x, which is approximately:
    # x_main (360) + ". Bio:" (6 chars) + dots (min 8) + space (1) = ~360 + 15*8.4 = ~486
    # SVG_WIDTH = 1024, so available width ≈ 1024 - 486 = 538px
    # In monospace 14px font, char width ≈ 8.4px, so chars ≈ 538/8.4 ≈ 64
    # Use a conservative estimate of 60 characters for safety
    if overflow_line_width is None:
        # Calculate based on SVG dimensions
        # bio_text_start_x ≈ x_main + (6 + min_dots + 1) * 8.4
        # Available width = SVG_WIDTH - bio_text_start_x
        # Convert to character count (char_width ≈ 8.4px)
        char_width = 8.4
        x_main = 360
        svg_width = 1024
        bio_text_start_x_approx = x_main + (6 + min_dots + 1) * char_width
        available_width_px = svg_width - bio_text_start_x_approx
        overflow_line_width = int(available_width_px / char_width) - 5  # Subtract 5 for safety margin
        overflow_line_width = max(50, min(overflow_line_width, 70))  # Clamp between 50-70

    # Calculate space for first line
    space_after_key = total_width - len(key_part)

    # If bio fits on first line with minimum dots
    if len(bio_text) + min_dots <= space_after_key:
        dots_needed = max(min_dots, space_after_key - len(bio_text) - 1)
        # Return structured format: (dots_part, bio_text_part)
        return (dots_needed, bio_text), []

    # If bio needs to overflow to additional lines
    # First line gets minimum dots and as much bio as possible without breaking words
    first_line_bio_space = space_after_key - min_dots - 1  # -1 for space before bio

    if first_line_bio_space > 0:
        # Find the best place to break without splitting words
        words = bio_text.split()
        first_line_bio = ""
        remaining_words = []

        for i, word in enumerate(words):
            # Check if adding this word would exceed the space
            test_line = first_line_bio + (" " if first_line_bio else "") + word
            if len(test_line) <= first_line_bio_space:
                first_line_bio = test_line
            else:
                # This word would exceed space, so put it and all remaining words on next lines
                remaining_words = words[i:]
                break

        remaining_bio = " ".join(remaining_words)
    else:
        first_line_bio = ""
        remaining_bio = bio_text

    # Calculate dots needed to fill the 75 character width
    first_line_length = len(key_part) + min_dots + (1 if first_line_bio else 0) + len(first_line_bio)
    additional_dots = total_width - first_line_length
    total_dots = min_dots + additional_dots

    # Return structured format: (dots_count, bio_text_part)
    first_line_data = (total_dots, first_line_bio)

    # Split remaining bio into multiple overflow lines (up to max_lines - 1 overflow lines)
    # All overflow lines are left-aligned and use overflow_line_width
    overflow_lines = []
    if remaining_bio:
        remaining_words = remaining_bio.split()
        max_overflow_lines = max_lines - 1  # Subtract 1 for the first line
        
        # Process words into lines
        current_line_words = []
        word_index = 0
        
        while word_index < len(remaining_words) and len(overflow_lines) < max_overflow_lines:
            word = remaining_words[word_index]
            # Test if adding this word would exceed the overflow line width
            test_line = " ".join(current_line_words + [word])
            
            if len(test_line) <= overflow_line_width:
                current_line_words.append(word)
                word_index += 1
            else:
                # Current line is full, save it and start a new line
                if current_line_words:
                    line_text = " ".join(current_line_words)
                    overflow_lines.append(("BIO_OVERFLOW", line_text))  # Left-aligned, no rjust
                    current_line_words = []
                else:
                    # Single word is too long, put it on its own line (truncate if needed)
                    if len(word) > overflow_line_width:
                        word = word[:overflow_line_width-3] + "..."
                    overflow_lines.append(("BIO_OVERFLOW", word))  # Left-aligned, no rjust
                    word_index += 1
                    if len(overflow_lines) >= max_overflow_lines:
                        break
        
        # Add the last line if there are remaining words
        if current_line_words and len(overflow_lines) < max_overflow_lines:
            line_text = " ".join(current_line_words)
            overflow_lines.append(("BIO_OVERFLOW", line_text))  # Left-aligned, no rjust

    return first_line_data, overflow_lines


def format_line(key, value, total_width=75, separator=":"):
    """Format a line to be exactly the specified width"""
    # Handle special cases for headers
    if key.startswith('—') or key.startswith('-'):
        # This is a header line
        return key + '—' * (total_width - len(key))

    # Handle bio overflow
    if key == "BIO_OVERFLOW":
        return value  # Already formatted as right-aligned

    # Regular key-value pair
    key_part = f". {key}{separator}"
    value_part = f" {value}"

    # Calculate dots needed
    dots_needed = total_width - len(key_part) - len(value_part)
    if dots_needed < 1:
        # If too long, truncate value
        available_for_value = total_width - len(key_part) - 1
        value_part = f" {value[:available_for_value - 3]}..."
        dots_needed = 1

    return f"{key_part}{'.' * dots_needed}{value_part}"


def format_username_header(full_name, username, total_width=75):
    """Format the username header line to be exactly the specified width"""
    # Clean the full name and get its visual length
    cleaned_name, name_visual_length = clean_and_visible_length(full_name)

    # Format: "Full Name -—- @username -——————————————————————-—-"
    username_part = f"@{username}"
    fixed_parts = " -—- " + username_part + " -"  # The fixed separator parts
    end_part = "—-—-"

    # Calculate visual length needed
    fixed_length = len(fixed_parts) + len(end_part)
    available_for_name = total_width - fixed_length

    # If the cleaned name is too long, truncate it
    if name_visual_length > available_for_name:
        # Truncate character by character until it fits
        truncated_name = ""
        current_length = 0
        for char in cleaned_name:
            char_width = 2 if unicodedata.east_asian_width(char) in ['F', 'W'] else 1
            if current_length + char_width + 3 > available_for_name:  # +3 for "..."
                truncated_name += "..."
                break
            truncated_name += char
            current_length += char_width
        cleaned_name = truncated_name
        name_visual_length = current_length + (3 if truncated_name.endswith("...") else 0)

    start_part = cleaned_name + fixed_parts

    # Calculate how many — characters needed in the middle
    middle_dashes_needed = total_width - len(start_part) - len(end_part)

    # Adjust for visual length differences (if any wide characters affect the calculation)
    visual_adjustment = name_visual_length - len(cleaned_name.replace("...", "")) - (
        3 if "..." in cleaned_name else 0)
    middle_dashes_needed -= visual_adjustment

    if middle_dashes_needed < 0:
        middle_dashes_needed = 0

    return f"{start_part}{'—' * middle_dashes_needed}{end_part}"


def format_styled_line_with_truncation(key, value, total_width=75):
    """Format a styled line with proper truncation that preserves XML structure"""
    # Handle headers first
    if key.startswith('—') or key.startswith('-'):
        header_line = key + '—' * (total_width - len(key))
        return f'<tspan class="separator">{header_line}</tspan>'

    # Handle bio overflow
    if key == "BIO_OVERFLOW":
        return f'<tspan class="value">{value}</tspan>'

    # For styled content, check the actual text length without styling tags
    key_part = f". {key}:"
    text_length = get_text_length_without_tags(value)

    # Calculate available space for the value part
    available_for_value = total_width - len(key_part) - 1  # -1 for minimum dots

    # If text is too long, create a simpler version without complex styling
    if text_length > available_for_value:
        # For very long content, create a simplified version
        simple_value = re.sub(r'<[^>]+>', '', value)  # Strip all tags
        if len(simple_value) > available_for_value:
            simple_value = simple_value[:available_for_value - 3] + "..."
        styled_value = f'<tspan class="value">{simple_value}</tspan>'
        dots_needed = max(1, total_width - len(key_part) - len(simple_value) - 1)
    else:
        styled_value = value
        dots_needed = max(1, total_width - len(key_part) - text_length - 1)

    dots = '.' * dots_needed

    return f'. <tspan class="key">{key}</tspan>:{dots} {styled_value}'


def get_content_lines(user):
    """Get content lines using the profile content definition function"""
    # Use the external content definition function
    base_lines = get_profile_content_definition(user)

    # Process bio line specially and add overflow line if needed
    processed_lines = []
    for key, value in base_lines:
        if key == "Bio":
            bio_data, overflow_lines = format_bio_line(value)
            # Store bio data as tuple (dots_count, bio_text)
            processed_lines.append(("Bio", bio_data))
            # Add overflow lines if any
            for overflow_key, overflow_value in overflow_lines:
                processed_lines.append((overflow_key, overflow_value))
        else:
            processed_lines.append((key, value))

    return processed_lines


def format_styled_line(key, value, special_styling=None):
    """Format and style a line in one step"""
    # Handle headers first
    if key.startswith('—') or key.startswith('-'):
        header_line = key + '—' * (75 - len(key))
        return f'<tspan class="separator">{header_line}</tspan>'

    # Handle bio overflow
    if key == "BIO_OVERFLOW":
        return f'<tspan class="value">{value}</tspan>'

    # Apply special styling if provided
    if special_styling and key in special_styling:
        styled_value = special_styling[key](value)
        return format_styled_line_with_truncation(key, styled_value)
    else:
        styled_value = f'<tspan class="value">{value}</tspan>'
        return format_styled_line_with_truncation(key, styled_value)


def calculate_account_age_years(created_at):
    """Calculate the age of the GitHub account in years"""
    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    current_date = datetime.now(created_date.tzinfo)
    age = current_date - created_date
    return max(1, age.days // 365 + 1)  # At least 1 year, round up


def calculate_language_percentages(language_stats):
    """Calculate language usage percentages based on commits"""
    total_commits = sum(lang['commits'] for lang in language_stats.values())
    if total_commits == 0:
        return {}

    percentages = {}
    for lang, stats in language_stats.items():
        if stats['commits'] > 0:
            percentages[lang] = {
                'percentage': (stats['commits'] / total_commits) * 100,
                'commits': stats['commits'],
                'additions': stats['additions'],
                'deletions': stats['deletions'],
                'net': stats['additions'] - stats['deletions'],
                'color': stats['color'],
                'repos': stats.get('repos', {})
            }

    # Sort by percentage
    return dict(sorted(percentages.items(), key=lambda x: x[1]['percentage'], reverse=True))


def generate_language_bar(language_percentages, width=400):
    """Generate SVG elements for language progress bar"""
    if not language_percentages:
        return []

    elements = []
    x_offset = 0

    for lang, stats in language_percentages.items():
        segment_width = (stats['percentage'] / 100) * width
        if segment_width < 1:  # Skip very small segments
            continue

        # Create colored rectangle for this language
        rect = f'<rect x="{x_offset}" y="0" width="{segment_width:.1f}" height="10" fill="{stats["color"]}" rx="1"/>'
        elements.append(rect)
        x_offset += segment_width

    return elements


class GitHubProfileGenerator:
    def __init__(self, token, username):
        self.token = token
        self.username = username
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        self.graphql_url = 'https://api.github.com/graphql'

    def check_is_authenticated_user(self, username):
        """Check if the token's authenticated user matches the provided username"""
        if not self.token:
            return False

        # Query to get the authenticated user's login
        query = """
        query {
            viewer {
                login
            }
        }
        """

        try:
            response = requests.post(
                self.graphql_url,
                json={'query': query},
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                if 'errors' not in data and data.get('data', {}).get('viewer'):
                    authenticated_username = data['data']['viewer'].get('login')
                    # Case-insensitive comparison since GitHub usernames are case-insensitive
                    return authenticated_username and authenticated_username.lower() == username.lower()
        except requests.RequestException as e:
            print(f"Error checking authenticated user: {e}")
            pass

        return False

    def fetch_all_commits_for_repo(self, owner, repo_name, from_date, to_date):
        """Fetch all commits for a specific repository using the REST API"""
        print(f"  Fetching additional commit data for {owner}/{repo_name}...")

        rest_api_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
        params = {
            "author": self.username,
            "since": from_date,
            "until": to_date,
            "per_page": 100
        }

        all_commits = []
        page = 1

        while True:
            params["page"] = page
            response = requests.get(rest_api_url, params=params, headers=self.headers)

            if response.status_code == 200:
                commits = response.json()
                if not commits:
                    break

                all_commits.extend(commits)
                page += 1

                if len(commits) < 100:  # Last page
                    break
            else:
                print(f"  ⚠ Failed to fetch commits for {owner}/{repo_name}: {response.status_code}")
                break

        return len(all_commits)

    def get_user_repositories(self):
        """Get a list of repositories that the user has contributed to"""
        query = """
        query($username: String!, $cursor: String) {
            user(login: $username) {
                repositories(first: 100, after: $cursor, orderBy: {field: PUSHED_AT, direction: DESC}) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        name
                        owner {
                            login
                        }
                        isPrivate
                        isFork
                        pushedAt
                        primaryLanguage {
                            name
                            color
                        }
                    }
                }
                repositoriesContributedTo(first: 100, after: $cursor, orderBy: {field: PUSHED_AT, direction: DESC}) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        name
                        owner {
                            login
                        }
                        isPrivate
                        isFork
                        pushedAt
                        primaryLanguage {
                            name
                            color
                        }
                    }
                }
            }
        }
        """

        repositories = []
        contributed_repos = []

        # First, fetch owned repositories
        has_next_page = True
        cursor = None

        while has_next_page:
            response = requests.post(
                self.graphql_url,
                json={'query': query, 'variables': {'username': self.username, 'cursor': cursor}},
                headers=self.headers
            )

            if response.status_code != 200:
                print(f"⚠ Failed to fetch repositories: {response.status_code}")
                break

            data = response.json()
            if 'errors' in data:
                print(f"⚠ GraphQL errors fetching repositories: {data['errors']}")
                break

            user_data = data.get('data', {}).get('user', {})

            # Process owned repositories
            repos = user_data.get('repositories', {})
            for repo in repos.get('nodes', []):
                if repo:
                    repositories.append(repo)

            # Process contributed repositories
            contrib_repos = user_data.get('repositoriesContributedTo', {})
            for repo in contrib_repos.get('nodes', []):
                if repo:
                    contributed_repos.append(repo)

            # Check pagination for owned repos
            page_info = repos.get('pageInfo', {})
            has_next_page = page_info.get('hasNextPage', False)
            cursor = page_info.get('endCursor') if has_next_page else None

        return repositories, contributed_repos

    def get_user_data_multi_year(self, years_back=None):
        """Fetch user data across multiple years including detailed issue and PR statistics with draft PRs"""
        end_date = datetime.now()

        # Get basic user info including detailed issue and PR statistics with draft PRs
        user_query = """
        query($username: String!) {
            user(login: $username) {
                name
                login
                email
                bio
                company
                location
                websiteUrl
                twitterUsername
                followers {
                    totalCount
                }
                following {
                    totalCount
                }
                repositories(ownerAffiliations: [OWNER]) {
                    totalCount
                }
                repositoriesContributedTo {
                    totalCount
                }
                starredRepositories {
                    totalCount
                }
                issues(states: [OPEN]) {
                    totalCount
                }
                closedIssues: issues(states: [CLOSED]) {
                    totalCount
                }
                pullRequests(states: [OPEN]) {
                    totalCount
                }
                draftPullRequests: pullRequests(states: [OPEN], first: 100) {
                    nodes {
                        isDraft
                    }
                    totalCount
                }
                mergedPullRequests: pullRequests(states: [MERGED]) {
                    totalCount
                }
                closedPullRequests: pullRequests(states: [CLOSED]) {
                    totalCount
                }
                createdAt
            }
        }
        """

        print(f"Fetching basic user info for {self.username}...")
        response = requests.post(
            self.graphql_url,
            json={'query': user_query, 'variables': {'username': self.username}},
            headers=self.headers
        )

        if response.status_code != 200:
            raise Exception(f"GraphQL query failed with status {response.status_code}: {response.text}")

        response_data = response.json()
        if 'errors' in response_data:
            raise Exception(f"GraphQL errors: {response_data['errors']}")

        if not response_data.get('data') or not response_data['data'].get('user'):
            raise Exception(f"User '{self.username}' not found or no access permissions")

        user_data = response_data['data']['user']
        print(f"✓ Found user: {user_data['name'] or user_data['login']}")

        # If years_back is not provided, calculate based on account age
        if years_back is None:
            years_back = calculate_account_age_years(user_data['createdAt'])
            print(f"✓ Using account age: {years_back} years")

        # Debug: Print the PR counts from GraphQL
        merged_prs_count = user_data.get('mergedPullRequests', {}).get('totalCount', 0)
        print(
            f"✓ GraphQL reports {merged_prs_count} merged PRs (this might include PRs from all time, not just recent years)")

        # Process draft PR data
        draft_prs = 0
        if user_data.get('draftPullRequests') and user_data['draftPullRequests'].get('nodes'):
            draft_prs = sum(1 for pr in user_data['draftPullRequests']['nodes'] if pr and pr.get('isDraft', False))

        # Add draft PR count to user data for later use
        user_data['draftPullRequests'] = {'totalCount': draft_prs}

        # Get contribution data for multiple years
        contributions_data = {}
        total_commits = 0
        language_stats = defaultdict(lambda: {
            'commits': 0,
            'additions': 0,
            'deletions': 0,
            'color': '#000000',
            'repos': {}  # Track commits per repo for each language
        })

        # Fetch the user's repositories and contributed repositories
        print("Fetching repositories the user has contributed to...")
        owned_repos, contributed_repos = self.get_user_repositories()

        # Combine all repositories for processing
        all_repos = owned_repos + contributed_repos
        print(f"✓ Found {len(owned_repos)} owned repositories and {len(contributed_repos)} contributed repositories")

        # Map of repo full names to their primary language
        repo_languages = {}
        for repo in all_repos:
            owner = repo.get('owner', {}).get('login', '')
            name = repo.get('name', '')
            full_name = f"{owner}/{name}"

            primary_lang = repo.get('primaryLanguage', {})
            if primary_lang and primary_lang.get('name'):
                lang_name = primary_lang['name']
                lang_color = primary_lang.get('color') or LANGUAGE_COLORS.get(lang_name, '#000000')
                repo_languages[full_name] = {
                    'name': lang_name,
                    'color': lang_color
                }

        # Fetch data year by year to avoid API limits
        current_year = end_date.year
        for year in range(current_year - years_back + 1, current_year + 1):
            year_start = f"{year}-01-01T00:00:00Z"
            year_end = f"{year}-12-31T23:59:59Z"

            print(f"Fetching contributions for {year}...")

            # First, get regular contributions via GraphQL
            contributions_query = """
            query($username: String!, $from: DateTime!, $to: DateTime!) {
                user(login: $username) {
                    contributionsCollection(from: $from, to: $to) {
                        totalCommitContributions
                        commitContributionsByRepository {
                            repository {
                                name
                                owner {
                                    login
                                }
                                primaryLanguage {
                                    name
                                    color
                                }
                                languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
                                    edges {
                                        size
                                        node {
                                            name
                                            color
                                        }
                                    }
                                }
                            }
                            contributions(first: 100) {
                                totalCount
                                nodes {
                                    commitCount
                                    occurredAt
                                }
                            }
                        }
                    }
                }
            }
            """

            response = requests.post(
                self.graphql_url,
                json={
                    'query': contributions_query,
                    'variables': {
                        'username': self.username,
                        'from': year_start,
                        'to': year_end
                    }
                },
                headers=self.headers
            )

            if response.status_code != 200:
                print(f"⚠ Warning: Failed to fetch data for {year}: {response.status_code}")
                continue

            response_data = response.json()
            if 'errors' in response_data:
                print(f"⚠ Warning: GraphQL errors for {year}: {response_data['errors']}")
                continue

            if not response_data.get('data') or not response_data['data'].get('user'):
                print(f"⚠ Warning: No user data returned for {year}")
                continue

            user_contrib = response_data['data']['user']
            if not user_contrib.get('contributionsCollection'):
                print(f"⚠ Warning: No contributions collection for {year}")
                continue

            year_data = user_contrib['contributionsCollection']
            contributions_data[year] = year_data
            year_commits_from_graphql = year_data.get('totalCommitContributions', 0)

            # Process GraphQL language statistics
            commit_contribs = year_data.get('commitContributionsByRepository', [])

            # Track repositories with few commits that might need additional REST API fetching
            small_repos = []

            for repo_contrib in commit_contribs:
                if not repo_contrib or not repo_contrib.get('repository'):
                    continue

                repo = repo_contrib['repository']
                repo_owner = repo.get('owner', {}).get('login', '')
                repo_name = repo.get('name', '')
                repo_full_name = f"{repo_owner}/{repo_name}"

                contributions = repo_contrib.get('contributions', {})
                commit_count = contributions.get('totalCount', 0) if contributions else 0

                # If repo has few commits, mark for additional fetching
                if commit_count < 10:
                    small_repos.append((repo_owner, repo_name))

                if commit_count == 0:
                    continue

                # Process all languages in repo (weighted by usage)
                languages = repo.get('languages', {})
                if languages and languages.get('edges'):
                    total_size = sum(edge.get('size', 0) for edge in languages['edges'] if edge and edge.get('size'))
                    if total_size > 0:
                        for edge in languages['edges']:
                            if not edge or not edge.get('node'):
                                continue

                            node = edge['node']
                            lang_name = node.get('name')
                            if not lang_name:
                                continue

                            lang_color = node.get('color') or LANGUAGE_COLORS.get(lang_name, '#000000')
                            edge_size = edge.get('size', 0)
                            lang_proportion = edge_size / total_size
                            weighted_commits = int(commit_count * lang_proportion)

                            if weighted_commits > 0:
                                language_stats[lang_name]['commits'] += weighted_commits
                                language_stats[lang_name]['color'] = lang_color
                                # Estimate additions/deletions (rough approximation)
                                language_stats[lang_name]['additions'] += int(edge_size * 0.3)
                                language_stats[lang_name]['deletions'] += int(edge_size * 0.1)

                                # Track commits per repo for this language
                                if repo_full_name not in language_stats[lang_name]['repos']:
                                    language_stats[lang_name]['repos'][repo_full_name] = 0
                                language_stats[lang_name]['repos'][repo_full_name] += weighted_commits
                    else:
                        # If no language data available, use primary language as fallback
                        primary_lang = repo.get('primaryLanguage')
                        if primary_lang and primary_lang.get('name'):
                            lang_name = primary_lang['name']
                            lang_color = primary_lang.get('color') or LANGUAGE_COLORS.get(lang_name, '#000000')
                            language_stats[lang_name]['commits'] += commit_count
                            language_stats[lang_name]['color'] = lang_color

                            # Track commits per repo for this language
                            if repo_full_name not in language_stats[lang_name]['repos']:
                                language_stats[lang_name]['repos'][repo_full_name] = 0
                            language_stats[lang_name]['repos'][repo_full_name] += commit_count
                else:
                    # If no languages data at all, fall back to primary language
                    primary_lang = repo.get('primaryLanguage')
                    if primary_lang and primary_lang.get('name'):
                        lang_name = primary_lang['name']
                        lang_color = primary_lang.get('color') or LANGUAGE_COLORS.get(lang_name, '#000000')
                        language_stats[lang_name]['commits'] += commit_count
                        language_stats[lang_name]['color'] = lang_color

                        # Track commits per repo for this language
                        if repo_full_name not in language_stats[lang_name]['repos']:
                            language_stats[lang_name]['repos'][repo_full_name] = 0
                        language_stats[lang_name]['repos'][repo_full_name] += commit_count

            # Now fetch additional commit data using REST API for repos with few commits
            year_commits_from_rest = 0

            print(f"  Checking {len(small_repos)} repositories with few commits for additional data...")
            for repo_owner, repo_name in small_repos:
                # Get additional commits using REST API
                additional_commits = self.fetch_all_commits_for_repo(
                    repo_owner,
                    repo_name,
                    year_start,
                    year_end
                )

                if additional_commits > 0:
                    repo_full_name = f"{repo_owner}/{repo_name}"
                    print(f"  ✓ Found {additional_commits} commits for {repo_full_name} via REST API")

                    # Only count additional commits beyond what GraphQL already reported
                    graphql_reported = 0
                    for repo_contrib in commit_contribs:
                        if not repo_contrib or not repo_contrib.get('repository'):
                            continue

                        repo = repo_contrib['repository']
                        if (repo.get('owner', {}).get('login', '') == repo_owner and
                                repo.get('name', '') == repo_name):
                            contributions = repo_contrib.get('contributions', {})
                            graphql_reported = contributions.get('totalCount', 0) if contributions else 0
                            break

                    if additional_commits > graphql_reported:
                        extra_commits = additional_commits - graphql_reported
                        year_commits_from_rest += extra_commits

                        # Update language stats for these additional commits
                        repo_lang = None
                        if repo_full_name in repo_languages:
                            repo_lang = repo_languages[repo_full_name]

                        if repo_lang:
                            lang_name = repo_lang['name']
                            lang_color = repo_lang['color']
                            language_stats[lang_name]['commits'] += extra_commits
                            language_stats[lang_name]['color'] = lang_color

                            # Track commits per repo
                            if repo_full_name not in language_stats[lang_name]['repos']:
                                language_stats[lang_name]['repos'][repo_full_name] = 0
                            language_stats[lang_name]['repos'][repo_full_name] += extra_commits

            # Total year commits = GraphQL reported + additional from REST API
            year_commits = year_commits_from_graphql + year_commits_from_rest
            total_commits += year_commits

            print(
                f"  ✓ {year}: {year_commits} total commits ({year_commits_from_graphql} from GraphQL, {year_commits_from_rest} additional from REST API)")

        print(f"✓ Total commits collected: {total_commits}")
        print(f"✓ Languages found: {len(language_stats)}")
        print(f"✓ Draft PRs found: {draft_prs}")

        return {
            'user': user_data,
            'total_commits': total_commits,
            'language_stats': dict(language_stats),
            'contributions_data': contributions_data
        }

    def generate_macos_window(self, content_svg, mode='dark'):
        """Wrap the content in a macOS-style window with only top titlebar"""
        if mode == 'dark':
            titlebar_bg = '#2c2c2e'
            title_text_color = '#ffffff'
            shadow_color = '#000000'
        else:
            titlebar_bg = '#e5e5e7'
            title_text_color = '#1d1d1f'
            shadow_color = '#00000040'

        # Window dimensions
        titlebar_height = 28
        bottom_padding = 28  # Added padding for bottom corner radius
        traffic_light_size = 12
        traffic_light_spacing = 8

        # Parse content SVG to get dimensions
        content_width = SVG_WIDTH
        content_height = 600  # Default fallback

        # Extract height from content SVG
        import re
        height_match = re.search(r'height="(\d+)px"', content_svg)
        if height_match:
            content_height = int(height_match.group(1))

        # Extract background color from content SVG
        bg_color = '#0d1117'  # Default dark background
        if mode == 'light':
            bg_color = '#f6f8fa'  # Default light background
        bg_match = re.search(r'<rect width="[^"]*" height="[^"]*" fill="([^"]*)"', content_svg)
        if bg_match:
            bg_color = bg_match.group(1)

        # Calculate window dimensions - add titlebar height and bottom padding
        window_width = content_width
        window_height = content_height + titlebar_height + bottom_padding

        # Generate window title
        window_title = f"Profile — {self.username}@github.com"

        window_svg = f'''<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="'Monaspace Krypton',monospace" width="{window_width}px" height="{window_height}px" font-size="14px">
<defs>
    <filter id="window-shadow" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="8" stdDeviation="16" flood-color="{shadow_color}" flood-opacity="0.3"/>
    </filter>
    <linearGradient id="titlebar-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="{titlebar_bg}"/>
        <stop offset="100%" stop-color="{titlebar_bg}"/>
    </linearGradient>
</defs>

<!-- Titlebar with rounded top corners only -->
<rect x="0" y="0" width="{window_width}" height="{titlebar_height}" rx="12" ry="12" fill="url(#titlebar-gradient)" filter="url(#window-shadow)"/>
<!-- Rectangle to square off bottom of titlebar -->
<rect x="0" y="{titlebar_height // 2}" width="{window_width}" height="{titlebar_height // 2}" fill="url(#titlebar-gradient)"/>

<!-- Bottom rounded corners -->
<rect x="0" y="{titlebar_height + content_height}" width="{window_width}" height="{bottom_padding}" rx="12" ry="12" fill="{bg_color}"/>
<!-- Rectangle to square off top of bottom rounded part -->
<rect x="0" y="{titlebar_height + content_height}" width="{window_width}" height="{bottom_padding // 2}" fill="{bg_color}"/>

<!-- Traffic lights -->
<circle cx="{12 + traffic_light_size // 2}" cy="{titlebar_height // 2}" r="{traffic_light_size // 2}" fill="#ff5f57"/>
<circle cx="{12 + traffic_light_size + traffic_light_spacing + traffic_light_size // 2}" cy="{titlebar_height // 2}" r="{traffic_light_size // 2}" fill="#ffbd2e"/>
<circle cx="{12 + traffic_light_size * 2 + traffic_light_spacing * 2 + traffic_light_size // 2}" cy="{titlebar_height // 2}" r="{traffic_light_size // 2}" fill="#28ca42"/>

<!-- Window title -->
<text x="{window_width // 2}" y="{titlebar_height // 2 + 4}" fill="{title_text_color}" font-size="13px" font-weight="500" text-anchor="middle" opacity="0.8">{window_title}</text>

<!-- Content area positioned directly below titlebar -->
<g transform="translate(0, {titlebar_height})">
'''

        # Extract the content from the original SVG and modify it to remove border radius
        content_start = content_svg.find('<style>')
        content_end = content_svg.rfind('</svg>')

        if content_start != -1 and content_end != -1:
            content_body = content_svg[content_start:content_end]
            # Remove the border radius from the background rectangle in window mode
            content_body = re.sub(r'<rect width="[^"]*" height="[^"]*" fill="[^"]*" rx="15"/>',
                                  lambda m: m.group(0).replace(' rx="15"', ''), content_body)
            window_svg += content_body

        window_svg += '''
</g>
</svg>'''

        return window_svg

    def generate_svg(self, data, mode='dark', macos_window=False):
        """Generate the complete SVG"""
        user = data['user']
        language_percentages = calculate_language_percentages(data['language_stats'])

        # Color schemes
        if mode == 'dark':
            bg_color = '#0d1117'  # Changed back to original GitHub dark theme color
            text_color = '#c9d1d9'
            key_color = '#ffa657'
            value_color = '#a5d6ff'
            add_color = '#3fb950'
            del_color = '#f85149'
            separator_color = text_color  # Set separator to same as text color
            green_color = '#238636'
            red_color = '#da3633'
            purple_color = '#8b5cf6'  # Purple for merged PRs
            gray_color = '#6e7681'  # Gray for draft PRs
            note_color = '#7c3aed'  # Purple for notes
            prompt_color = '#39d353'  # Green for shell prompt
            cursor_color = '#f0f6fc'  # Light color for cursor
        else:
            bg_color = '#f6f8fa'
            text_color = '#24292f'
            key_color = '#953800'
            value_color = '#0a3069'
            add_color = '#1a7f37'
            del_color = '#cf222e'
            separator_color = text_color  # Set separator to same as text color
            green_color = '#1a7f37'
            red_color = '#cf222e'
            purple_color = '#7c3aed'  # Purple for merged PRs
            gray_color = '#656d76'  # Gray for draft PRs
            note_color = '#7c3aed'  # Purple for notes
            prompt_color = '#1a7f37'  # Green for shell prompt
            cursor_color = '#24292f'  # Dark color for cursor

        # Use the global constants for dimensions
        svg_width = SVG_WIDTH
        line_height = 18
        top_margin = 35

        # Dynamically calculate content lines
        content_lines = get_content_lines(user)

        # Count different types of lines
        text_lines_count = len([line for line in content_lines if line[0] != "GAP"])
        gap_lines_count = len([line for line in content_lines if line[0] == "GAP"])

        # Count language details (top 10 languages shown)
        language_details_count = min(10, len(language_percentages)) if language_percentages else 0

        # Calculate total content lines
        total_content_lines = (
                1 +  # User header
                text_lines_count +
                gap_lines_count +
                language_details_count
        )

        # Calculate content height including notes and prompt at the bottom
        content_height = (
                (total_content_lines * line_height) +  # All text lines
                10 +  # Language bar height
                35 +  # Space between language bar and language details (increased from 25)
                15 +  # Space after language details
                20 +  # Space before notes
                20 +  # First note line
                15 +  # Space for possible second note line
                25 +  # Space before prompt (increased from 15)
                20  # Prompt line
        )

        # Take the maximum of ASCII art height and content height, add minimal padding
        # If SVG_HEIGHT is specified, use it; otherwise calculate dynamically
        if SVG_HEIGHT is not None:
            svg_height = SVG_HEIGHT
        else:
            svg_height = max(ASCII_HEIGHT + top_margin, content_height) + 5

        print(f"Debug: Content lines: {len(content_lines)}, Language details: {language_details_count}")
        print(f"Debug: Total lines: {total_content_lines}, SVG height: {svg_height}")

        # Determine border radius based on whether this will be wrapped in a window
        border_radius = "0" if macos_window else "15"

        # Start building SVG with updated font and styling
        svg_content = f'''<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="'Monaspace Krypton',monospace" width="{svg_width}px" height="{svg_height}px" font-size="14px">
<style>
@import url("https://cdn.jsdelivr.net/gh/iXORTech/webfonts@main/monaspace/krypton/krypton.css");
.key {{fill: {key_color}; font-weight: bold;}}
.value {{fill: {value_color};}}
.addColor {{fill: {add_color};}}
.delColor {{fill: {del_color};}}
.separator {{fill: {separator_color};}}
.green {{fill: {green_color};}}
.red {{fill: {red_color};}}
.purple {{fill: {purple_color};}}
.gray {{fill: {gray_color};}}
.note {{fill: {note_color}; font-size: 12px;}}
.prompt {{fill: {prompt_color}; font-size: 14px;}}
.cursor {{fill: {cursor_color};}}
text, tspan {{white-space: pre;}}

@keyframes blink {{
    0%, 50% {{ opacity: 1; }}
    51%, 100% {{ opacity: 0; }}
}}

.blinking {{
    animation: blink 1s infinite;
}}
</style>
<rect width="{svg_width}px" height="{svg_height}px" fill="{bg_color}" rx="{border_radius}"/>'''

        # ASCII art positioned at x=25
        ascii_x = 25
        svg_content += f'''
<text x="{ascii_x}" y="30" fill="{text_color}" class="ascii">
    <tspan x="{ascii_x}" y="50">           ____</tspan>
    <tspan x="{ascii_x}" y="66">          /\   \</tspan>
    <tspan x="{ascii_x}" y="82">         /  \   \</tspan>
    <tspan x="{ascii_x}" y="98">        /    \   \</tspan>
    <tspan x="{ascii_x}" y="114">       /      \   \</tspan>
    <tspan x="{ascii_x}" y="130">      /   /\   \   \</tspan>
    <tspan x="{ascii_x}" y="146">     /   /  \   \   \</tspan>
    <tspan x="{ascii_x}" y="162">    /   /    \   \   \</tspan>
    <tspan x="{ascii_x}" y="178">   /   /    / \   \   \</tspan>
    <tspan x="{ascii_x}" y="194">  /   /    /   \   \   \</tspan>
    <tspan x="{ascii_x}" y="210"> /   /    /---------'   \</tspan>
    <tspan x="{ascii_x}" y="226">/   /    /_______________\</tspan>
    <tspan x="{ascii_x}" y="242">\  /                     /</tspan>
    <tspan x="{ascii_x}" y="258"> \/_____________________/</tspan>
</text>'''

        # Main content starts at x=360
        x_main = 360
        y_start = top_margin

        # User header - use dash format for all usernames, handling invisible characters
        display_name = user.get('name') or user.get('login', 'Unknown')
        username = user.get('login', 'Unknown')

        # Always use the dash format for every username
        header_line = format_username_header(display_name, username, 75)

        svg_content += f'''
<text x="{x_main}" y="{y_start}" fill="{text_color}" font-size="14px">
<tspan x="{x_main}" y="{y_start}">{header_line}</tspan>
</text>'''

        y_current = y_start + 25

        # Get stats with safe access
        repos_owned = user.get('repositories', {}).get('totalCount', 0) if user.get('repositories') else 0
        repos_contributed = user.get('repositoriesContributedTo', {}).get('totalCount', 0) if user.get(
            'repositoriesContributedTo') else 0
        stars = user.get('starredRepositories', {}).get('totalCount', 0) if user.get('starredRepositories') else 0
        followers = user.get('followers', {}).get('totalCount', 0) if user.get('followers') else 0
        open_issues = user.get('issues', {}).get('totalCount', 0) if user.get('issues') else 0
        closed_issues = user.get('closedIssues', {}).get('totalCount', 0) if user.get('closedIssues') else 0
        open_prs = user.get('pullRequests', {}).get('totalCount', 0) if user.get('pullRequests') else 0
        draft_prs = user.get('draftPullRequests', {}).get('totalCount', 0) if user.get('draftPullRequests') else 0
        merged_prs = user.get('mergedPullRequests', {}).get('totalCount', 0) if user.get('mergedPullRequests') else 0
        closed_prs = user.get('closedPullRequests', {}).get('totalCount', 0) if user.get('closedPullRequests') else 0

        # Calculate non-draft open PRs
        non_draft_open_prs = open_prs - draft_prs

        # Define special styling for lines with colored content - with pipe separators outside spans
        special_styling = {
            "Repository": lambda
                value: f'<tspan class="value">{repos_owned} (<tspan class="key">Contributed</tspan>: {repos_contributed})</tspan> | <tspan class="value"><tspan class="key">Stars</tspan>: {stars}</tspan> | <tspan class="value"><tspan class="key">Followers</tspan>: {followers}</tspan>',
            "Commits": lambda
                value: f'<tspan class="value">{data["total_commits"]:,}</tspan>',
            "Issues": lambda
                value: f'<tspan class="value"><tspan class="key">Open</tspan>: <tspan class="green">{open_issues}</tspan></tspan> | <tspan class="value"><tspan class="key">Closed</tspan>: <tspan class="red">{closed_issues}</tspan></tspan>',
            "Pull Requests": lambda
                value: f'<tspan class="value"><tspan class="key">Open</tspan>: <tspan class="green">{non_draft_open_prs}</tspan></tspan> | <tspan class="value"><tspan class="key">Draft</tspan>: <tspan class="gray">{draft_prs}</tspan></tspan> | <tspan class="value"><tspan class="key">Merged</tspan>: <tspan class="purple">{merged_prs}</tspan></tspan> | <tspan class="value"><tspan class="key">Closed</tspan>: <tspan class="red">{closed_prs}</tspan></tspan>'
        }

        # Render all content lines dynamically
        bio_text_start_x = None  # Track the x position where bio text starts (for alignment)
        for key, value in content_lines:
            if key == "GAP":
                # Add gap (just increase y_current)
                y_current += line_height
                continue

            # Handle Bio specially - value is a tuple (dots_count, bio_text)
            if key == "Bio":
                dots_count, bio_text = value
                # Create the line with proper styling: dots are normal text color, bio text is blue
                styled_line = f'. <tspan class="key">Bio</tspan>:{"." * dots_count}'
                if bio_text:
                    styled_line += f' <tspan class="value">{bio_text}</tspan>'
                    # Calculate bio text start position for alignment
                    # ". Bio:" = 6 chars, dots = dots_count chars, space = 1 char
                    # In monospace font (14px), approximate char width is 8.4px
                    char_width = 8.4
                    bio_text_start_x = x_main + (6 + dots_count + 1) * char_width
            elif key == "BIO_OVERFLOW":
                # Use bio_text_start_x if available, otherwise use x_main
                overflow_x = bio_text_start_x if bio_text_start_x is not None else x_main
                styled_line = f'<tspan class="value">{value}</tspan>'
                svg_content += f'''
<text x="{overflow_x}" y="{y_current}" fill="{text_color}" font-size="14px">
<tspan x="{overflow_x}" y="{y_current}">{styled_line}</tspan>
</text>'''
                y_current += line_height
                continue
            # Replace placeholder values for GitHub Statistics - just pass placeholders as special styling handles the formatting
            elif key in ["Repository", "Commits", "Issues", "Pull Requests"]:
                value = "PLACEHOLDER"  # Will be replaced by special styling
                styled_line = format_styled_line(key, value, special_styling)
            else:
                styled_line = format_styled_line(key, value, special_styling)

            svg_content += f'''
<text x="{x_main}" y="{y_current}" fill="{text_color}" font-size="14px">
<tspan x="{x_main}" y="{y_current}">{styled_line}</tspan>
</text>'''
            y_current += line_height

        # Language progress bar and stats (no spacing before bar)
        if language_percentages:
            # Add progress bar - width 560
            svg_content += f'<g transform="translate({x_main}, {y_current})">'
            bar_elements = generate_language_bar(language_percentages, 560)
            for element in bar_elements:
                svg_content += f'  {element}'
            svg_content += '</g>'

            y_current += 35  # Spacing after language bar before language details

            # Language details
            for i, (lang, stats) in enumerate(list(language_percentages.items())[:10]):  # Show top 10 languages
                percentage_str = f"{stats['percentage']:.1f}%"
                commits_str = f"{stats['commits']:,} commits"

                svg_content += f'''
<text x="{x_main}" y="{y_current}" fill="{text_color}" font-size="14px">
<tspan x="{x_main}" y="{y_current}">  <tspan style="fill:{stats['color']}">●</tspan> <tspan class="key">{lang}</tspan>: <tspan class="value">{percentage_str}</tspan> <tspan class="value">{commits_str}</tspan></tspan>
</text>'''
                y_current += line_height

        # Add notes at the bottom, aligned with ASCII art (x=25)
        y_current += 20  # Space before notes

        # Generate timestamp (current UTC time)
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Add generation timestamp note
        svg_content += f'''
<text x="{ascii_x}" y="{y_current}" fill="{text_color}" class="note">
<tspan x="{ascii_x}" y="{y_current}" class="note">Generated on {current_time}</tspan>
</text>'''

        # Check if the token's authenticated user matches the provided username
        if self.token:  # Only check if token is provided
            is_authenticated_user = self.check_is_authenticated_user(self.username)
            if is_authenticated_user:
                y_current += 15  # Space for second note
                svg_content += f'''
<text x="{ascii_x}" y="{y_current}" fill="{text_color}" class="note">
<tspan x="{ascii_x}" y="{y_current}" class="note">These metrics include private contributions.</tspan>
</text>'''

        # Add shell prompt with flashing cursor
        y_current += 25
        prompt_text = f"{self.username}@github.com:~$"

        svg_content += f'''
<text x="{ascii_x}" y="{y_current}" fill="{text_color}" class="prompt">
<tspan x="{ascii_x}" y="{y_current}" class="prompt">{prompt_text} </tspan><tspan class="cursor blinking">█</tspan>
</text>'''

        svg_content += '\n</svg>'

        # If macOS window is requested, wrap the content
        if macos_window:
            svg_content = self.generate_macos_window(svg_content, mode)

        return svg_content


def main():
    parser = argparse.ArgumentParser(description='Generate GitHub profile SVGs with language statistics')
    parser.add_argument('--token', help='GitHub Personal Access Token (defaults to GITHUB_TOKEN env var)')
    parser.add_argument('--username', help='GitHub Username (defaults to GITHUB_USERNAME env var)')
    parser.add_argument('--years', type=int, help='Number of years of data to fetch (defaults to account age)')
    parser.add_argument('--output-dark', default='dark.svg', help='Output file for dark mode SVG')
    parser.add_argument('--output-light', default='light.svg', help='Output file for light mode SVG')
    parser.add_argument('--macos-window', action='store_true', help='Wrap output in macOS-style window')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')

    args = parser.parse_args()

    # Get token from argument or environment variable
    token = args.token or os.getenv('GITHUB_TOKEN')
    if not token:
        print("Error: GitHub token is required. Provide it via --token argument or GITHUB_TOKEN environment variable.")
        return 1

    # Get username from argument or environment variable
    username = args.username or os.getenv('GITHUB_USERNAME')
    if not username:
        print("Error: GitHub username is required. Provide it via --username argument or GITHUB_USERNAME environment variable.")
        return 1

    try:
        print(f"Fetching GitHub data for {username}...")
        generator = GitHubProfileGenerator(token, username)

        if args.years:
            print(f"Collecting {args.years} years of contribution data...")
        else:
            print("Collecting contribution data for entire account history...")

        data = generator.get_user_data_multi_year(args.years)

        print("Generating dark mode SVG...")
        dark_svg = generator.generate_svg(data, mode='dark', macos_window=args.macos_window)
        with open(args.output_dark, 'w', encoding='utf-8') as f:
            f.write(dark_svg)

        print("Generating light mode SVG...")
        light_svg = generator.generate_svg(data, mode='light', macos_window=args.macos_window)
        with open(args.output_light, 'w', encoding='utf-8') as f:
            f.write(light_svg)

        window_suffix = " (with macOS window)" if args.macos_window else ""
        print(f"\nGenerated successfully{window_suffix}!")
        print(f"Dark mode: {args.output_dark}")
        print(f"Light mode: {args.output_light}")

        # Print some statistics
        language_stats = calculate_language_percentages(data['language_stats'])
        if language_stats:
            print(f"\nTop languages:")
            for i, (lang, stats) in enumerate(list(language_stats.items())[:10]):
                print(f"  {i + 1}. {lang}: {stats['percentage']:.1f}% ({stats['commits']:,} commits)")
                # List all repositories for this language
                if stats.get('repos'):
                    # Sort repos by commit count in descending order
                    sorted_repos = sorted(stats['repos'].items(), key=lambda x: x[1], reverse=True)
                    for repo, commits in sorted_repos:
                        print(f"      - {repo}: {commits:,} commits")
        else:
            print("\nNo language statistics found.")

    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
