# Online Cinema 🎬

An online cinema application built with **FastAPI**, **SQLAlchemy**, and **SQLite**. Provides functionality for user authentication, movie listing, cart & orders, reactions/comments.

---

## Table of Contents

- [Features](#features)  
- [Technologies](#technologies)  
- [Getting Started](#getting-started)  
  - [Prerequisites](#prerequisites)  
  - [Clone & Setup](#clone--setup)  
  - [Configuration](#configuration)  
  - [Database Migrations](#database-migrations)  
  - [Running the App](#running-the-app)  
- [API Endpoints](#api-endpoints)  
  - [Auth](#auth)  
  - [Movies](#movies)  
  - [Cart](#cart)  
  - [Orders](#orders)  
- [Running Tests](#running-tests)

---

## Features

- User registration, activation, login & logout  
- Browse, filter, search movies  
- Movie details, reactions (like / dislike), comments  
- Shopping cart: add, remove, clear, ready to add payments 
- Order creation, cancellation, listing  
- Admin‑protected routes for order management  

---

## Technologies

- **Python 3.x**  
- **FastAPI** for API framework  
- **SQLAlchemy (async)** for ORM / DB access  
- **SQLite** (for development & tests); can be swapped for PostgreSQL, etc.  
- **Pydantic** for data validation  
- **Alembic** for migrations  
- **Pytest** / `pytest‑asyncio` for testing  

---

## Getting Started

### Prerequisites

Make sure you have:

- Python 3.9+ installed  
- (Optional) virtual environment tool, e.g. `venv` or `virtualenv`  
- SQLite available (if using SQLite) or a database of your choice  

---

### Clone & Setup

```bash
git clone https://github.com/Andreyome/online-cinema.git
cd online-cinema
python -m venv .venv
source .venv/bin/activate     # or on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

### Configuration

- Copy `.env.sample` to `.env`  
- Edit `.env` to provide necessary configuration values, e.g.:

  ```
  SECRET_KEY=your_secret_key
  DATABASE_URL=sqlite+aiosqlite:///./dev.db
  ```

---

### Database Migrations

You’ll need to set up the database and run migrations:

```bash
alembic upgrade head
```

This will create all necessary tables.

If you change models, generate new migration:

```bash
alembic revision --autogenerate -m "Describe change"
alembic upgrade head
```

---

### Running the App

Start the server using Uvicorn:

```bash
uvicorn src.main:app --reload
```

- Opens on `http://127.0.0.1:8000` by default  
- API documentation available at `http://127.0.0.1:8000/docs`  


---

## API Endpoints

Here are the main endpoints:

### Auth

| Method                                | Route                                                                                                          |
|---------------------------------------|----------------------------------------------------------------------------------------------------------------|
| `POST /api/v1/auth/register`          | register a user                                                                                                |
| `POST /api/v1/auth/login`             | login (returns access/refresh tokens)                                                                          |
| `POST /api/v1/auth/logout`            | logout, invalidating access token                                                                              |
| `GET /api/v1/auth/activate`           | activate account                                                                                               |
| `POST /api/v1/auth/resend-activation` | resend activation email with new activation token                                                              |
| `POST /api/v1/auth/refresh`           | uses a valid refresh token to issue a new, short-lived access token without requiring the user to log in again |
| `POST /api/v1/auth/reset-password`    | verifies a password reset token and updates the user's password.                                               |                                                                                                                |
| `POST /api/v1/auth/change-password`   | allows an authenticated user to change their password by providing the old and new passwords                   |                                                                                                                |
| `POST /api/v1/auth/forgot-password`   | sends a password reset link to the user's email                                                                |                                                                                                                |


### Movies

| Method   | Endpoint                                             | Description                                |
|----------|------------------------------------------------------|--------------------------------------------|
| GET      | /movies/                                             | List all movies (with filters, pagination) | 
| GET      | /movies/{movie_id}                                   | Get details of a single movie              |
| POST     | /movies/                                             | Create a new movie                         |
| PUT      | /movies/{movie_id}                                   | Update a movie                             |
| DELETE   | /movies/{movie_id}                                   | Delete a movie                             |
| POST     | /movies/{movie_id}/reactions/like                    | Like a movie                               |
| POST     | /movies/{movie_id}/reactions/dislike                 | Dislike a movie                            | 
| DELETE   | /movies/{movie_id}/reactions                         | Remove user’s reaction from a movie        |
| GET      | /movies/{movie_id}/reactions                         | Get total likes/dislikes for a movie       | 
| POST     | /movies/{movie_id}/comments                          | Add a comment to a movie                   | 
| GET      | /movies/{movie_id}/comments                          | List all comments for a movie              | 
| PUT      | /movies/{movie_id}/comments/{comment_id}             | Update a comment                           |
| DELETE   | /movies/{movie_id}/comments/{comment_id}             | Delete a comment                           | 
| POST     | /movies/{movie_id}/comments/{comment_id}/like        | Like a comment                             | 
| POST     | /movies/{movie_id}/comments/{comment_id}/dislike     | Dislike a comment                          | 
| DELETE   | /movies/{movie_id}/comments/{comment_id}/reactions   | Remove user’s reaction from a comment      | 
| GET      | /movies/{movie_id}/comments/{comment_id}/reactions   | Get likes/dislikes count for a comment     | 


### Cart

| Endpoint                         | Description                                   |
|----------------------------------|-----------------------------------------------|
| `GET /cart/`                     | get the user's cart (creates if none)         |
| `POST /cart/add/{movie_id}`      | add movie to cart                             |
| `DELETE /cart/remove/{movie_id}` | remove movie from cart                        |
| `POST /cart/pay`                 | simulate payment of cart (moves to purchases) |
| `DELETE /cart/clear`             | clear all items from cart                     |

### Orders

| Endpoint                           | Description                                                   |
|------------------------------------|---------------------------------------------------------------|
| `POST /orders/`                    | create order from cart                                        |
| `PATCH /orders/{order_id}/cancel/` | cancel a pending order                                        |
| `GET /orders/`                     | get all orders for current user                               |
| `GET /admin/orders`                | admin-only: list all orders with filters, sorting, pagination |

---

## Running Tests

```bash
pytest
```
---

