
# Wine Cellar

**Wine Cellar** is a self-hosted wine management app built with Django, designed for wine enthusiasts who want to keep track of the wines they've tried, store tasting notes, rate wines, and manage their wine inventory. Whether you're a casual wine drinker or a connoisseur with a growing collection, this app helps you organize and enjoy your wine journey. Additionally, you can add food pairings to wines for the perfect dining experience.

<img src="https://github.com/user-attachments/assets/315280b8-9f87-45fd-ab88-507d88aef362" height="150" alt="Landing page showing different statistics about your wines">
<img src="https://github.com/user-attachments/assets/645855e4-3c22-4253-9d59-9fd76f7f4c05" height="150" alt="Wine list view showing all wines in the database">
<img src="https://github.com/user-attachments/assets/dec2345b-e276-43bf-aac9-e667f3a535b3" height="150" alt="wine detail view showing a picture of a wine and it's attributes">

## Features

- **Wine Tracking**: Record wines you've tasted and whether you liked or disliked them.
- **Inventory Management**: Keep track of how many bottles you have in stock.
- **Tasting Notes**: Add detailed notes to remember the aroma, flavor, and overall experience.
- **Wine Ratings**: Rate each wine on a scale to keep track of your preferences.
- **Food Pairings**: Add suggested food pairings to wines to complement your tastings.
- **Self-hosted**: Complete control over your data, running on your own server.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [Clone the Repository](#1-clone-the-repository)
  - [Install Dependencies](#2-install-dependencies)
  - [Run the Development Server](#3-run-the-development-server)
  - [Watch for Changes](#4-watch-for-changes)
  - [Create a User](#5-create-a-user)
  - [Load Fixtures](#6-load-fixtures)
- [Directory Structure](#directory-structure)
- [Running Tests](#running-tests)
- [Additional Information](#additional-information)

---

## Prerequisites

Before you begin, ensure your machine has the following installed:

- [Python 3.x](https://www.python.org/downloads/) (for the backend)
- [Node.js](https://nodejs.org/) (v14.x or higher recommended, for the frontend)
- [npm](https://www.npmjs.com/get-npm) (comes with Node.js)

---

## Getting Started

Follow these steps to set up and run the Wine Cellar app:

### 1. Clone the Repository

Clone the repository to your local machine and navigate into the project folder:

```sh
git clone https://github.com/yourusername/wine-cellar.git
cd wine-cellar
```

### 2. Install Dependencies

This command will set up a Python virtual environment, install Python dependencies, install npm packages, build the frontend, and apply database migrations:

```sh
make install
```

### 3. Run the Development Server

To start the Django development server, use:

```sh
make server
```

By default, the server will run at `http://127.0.0.1:8003/`.

### 4. Watch for Changes

To automatically rebuild the frontend and restart the backend server on file changes, run:

```sh
make watch
```

### 5. Create a User

Create an admin user for managing the app by running the following:

```sh
source venv/bin/activate
python manage.py createsuperuser
```

### 6. Load Fixtures (Optional)

If you want to load some initial data (e.g., sample wines, categories), run:

```sh
make fixtures
```

---

## Directory Structure

Here's an overview of the project structure:

- `wine_cellar/`: Main application code (Django app for wines, inventory, ratings, etc.).
- `tests/`: Test cases for the application (both backend and frontend).
- `node_modules/`: Directory for npm packages (installed dependencies for the frontend).
- `venv/`: Python virtual environment (isolated dependencies for the backend).
- `Makefile`: A file containing predefined commands for setup and running the app.

---

## Running Tests

To run the full test suite (both Django and frontend tests), use:

```sh
make test
```

You can also run Django backend tests directly using:

```sh
python manage.py test
```

---

## Additional Information

For more details on how to use specific commands or customize the setup, refer to the `Makefile` in the root directory of the repository. You can also check the official Django and Node.js documentation for more information on extending or modifying the application.
