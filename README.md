# Wine Cellar

## Prerequisites

Before you begin, ensure you have the following installed on your machine:
- Python 3.x
- Node.js and npm

## Getting Started

Follow these steps to get the application up and running:

### 1. Clone the Repository

```sh
git clone https://github.com/yourusername/generic-app.git
cd generic-app
```

### 2. Install Dependencies

This command will install the necessary npm packages, build the frontend, set up a virtual environment for Python, install Python dependencies, and run database migrations.

```sh
make install
```

### 3. Run the Development Server

To start the Django development server, run:

```sh
make server
```

By default, the server will run at `http://127.0.0.1:8003/`.

### 4. Watch for Changes

To automatically rebuild the frontend and restart the backend server on code changes, use:

```sh
make watch
```

### 5. Create a user
```
source venv/bin/activate
python manage.py createsuperuser
```

### 6. Load Fixtures

To load initial data into your database, use:

```sh
make fixtures
```

## API Server
Needs https://github.com/goapunk/wine-cellar-api running to use the search


## Directory Structure

- `wine_cellar/`: Main application code.
- `tests/`: Test cases for the application.
- `node_modules/`: Directory for npm packages.
- `venv/`: Python virtual environment.

## Additional Information

For more details on each command or to customize the setup, refer to the `Makefile` in the root directory of the repository.


