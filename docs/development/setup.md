# Installation

## Docker Deployment

### Development / Demo Mode

!!! Warning

    Don't use this in production.

#### Steps:

1. Copy the development environment configuration:
   ```sh
   cp .env.dev-sample .env.dev
   ```
2. Build the Docker image:
   ```sh
   docker build -t wine-cellar-dev .
   ```
3. Start the application:
   ```sh
   docker compose up
   ```
4. (optional): populate database with some sample data:
   ```sh
   make docker-fixtures
   ```

---

## Local Setup
### Prerequisites

Ensure your system has:

- [Python 3.x](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/) (v24.x or higher recommended)
- [npm](https://www.npmjs.com/get-npm) (comes with Node.js)

### Getting Started

#### 1. Clone the Repository

```sh
git clone https://github.com/the-broke-sommeliers/wine-cellar.git
cd wine-cellar
```

#### 2. Install Dependencies

```sh
make install
```

#### 3. Run the Development Server

```sh
make server
```

Access the app at `http://127.0.0.1:8003/`.

#### 4. Watch for Changes

```sh
make watch
```

#### 5. Load Sample Data (Optional)

```sh
make fixtures
```
This will create an admin user with login `admin:password`.

#### 6. Create an Admin User (Optional)

```sh
source venv/bin/activate
python manage.py createsuperuser
```
If you haven't run step 5.