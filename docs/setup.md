# Installation & Setup

## Prerequisites

Ensure your system has:

- [Python 3.x](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/) (v14.x or higher recommended)
- [npm](https://www.npmjs.com/get-npm) (comes with Node.js)

## Getting Started

### 1. Clone the Repository

```sh
git clone https://github.com/yourusername/wine-cellar.git
cd wine-cellar
```

### 2. Install Dependencies

```sh
make install
```

### 3. Run the Development Server

```sh
make server
```

Access the app at `http://127.0.0.1:8003/`.

### 4. Watch for Changes

```sh
make watch
```

### 5. Create an Admin User

```sh
source venv/bin/activate
python manage.py createsuperuser
```

### 6. Load Sample Data (Optional)

```sh
make fixtures
```
