# Installation

## Docker Deployment

### Development / Demo Mode

!!! Warning

    Don't use this in production.

#### Steps:

1. Start the application:
   ```sh
   make docker-server
   ```
   This copies `.env.dev-sample` to `.env.dev` (if it doesn't exist yet),
   builds the Docker image, and starts the stack. Equivalent to running
   these manually:
   ```sh
   cp .env.dev-sample .env.dev
   docker build -t wine-cellar-dev .
   docker compose up
   ```
2. (optional): populate database with some sample data:
   ```sh
   make docker-fixtures
   ```

---

## Local Setup
### Prerequisites

Ensure your system has:

- [Python 3.x](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/) (v24.x or higher recommended)

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

#### 3. Load Sample Data (Optional)

```sh
make fixtures
```
This will create an admin user with login `admin:password`.

#### 4. Run the Development Server

```sh
make watch
```

Access the app at `http://127.0.0.1:8003/`.