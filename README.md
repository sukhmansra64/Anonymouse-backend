# Backend

This is a FastAPI-based chatroom application that supports user authentication, chatroom creation, message management, and real-time communication using Socket.IO.

---

## Features

1. **User Management**
   - Register new users.
   - Login with JWT authentication.
   - Update and delete user accounts.

2. **Chatroom Management**
   - Create chatrooms.
   - Join or leave chatrooms.
   - List all chatrooms or only the ones you belong to.

3. **Messaging**
   - Send and receive messages in chatrooms.
   - Retrieve message history for a chatroom.

4. **Real-Time Communication**
   - Join and leave chatrooms in real-time.
   - Broadcast messages and notifications to chatroom members using Socket.IO.

---

## Getting Started

### Prerequisites

- Python 3.10+
- MongoDB (Use MongoDB Atlas or a local MongoDB instance)
- Node.js (optional for testing with Socket.IO client libraries)

### Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/your-repo/chatroom-app.git
    cd chatroom-app
    ```

2. Create a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate   # On Windows: venv\Scripts\activate
    ```

3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Create a `.env` file in the root directory with the following content:

    ```env
    MONGO_URI=your_mongodb_connection_string
    JWT_SECRET=your_secret_key
    JWT_ALGO=algoirthm_of_your_choosing
    ```

5. Run the application:

    ```bash
    uvicorn app.server.app:app --host 0.0.0.0 --port 8000 --reload
    ```

---

## API Endpoints

### User Routes

| Method  | Endpoint            | Description                | Authentication Required |
|---------|---------------------|----------------------------|--------------------------|
| `POST`  | `/api/user/`        | Create a new user          | No                       |
| `POST`  | `/api/user/login`   | Login and get JWT token    | No                       |
| `GET`   | `/api/user/`        | Get all users              | Yes                      |
| `GET`   | `/api/user/{id}`    | Get user by ID             | Yes                      |
| `PUT`   | `/api/user/{id}`    | Update user details        | Yes (self-update only)   |
| `DELETE`| `/api/user/{id}`    | Delete user account        | Yes (self-delete only)   |

---

### Chatroom Routes

| Method  | Endpoint                    | Description                      | Authentication Required |
|---------|-----------------------------|----------------------------------|--------------------------|
| `GET`   | `/api/chatroom/`            | Get all chatrooms (user's only)  | Yes                      |
| `POST`  | `/api/chatroom/`            | Create a chatroom                | Yes                      |
| `GET`   | `/api/chatroom/{id}`        | Get a chatroom by ID (if member) | Yes                      |
| `POST`  | `/api/chatroom/{id}/join`   | Join a chatroom                  | Yes                      |

---

### Message Routes

| Method  | Endpoint                  | Description                      | Authentication Required |
|---------|---------------------------|----------------------------------|--------------------------|
| `POST`  | `/api/message/`           | Send a message to a chatroom     | Yes                      |
| `GET`   | `/api/message/{chatroom}` | Get all messages in a chatroom   | Yes (must be a member)   |

---

## Real-Time Communication with Socket.IO

### Events

#### Connection Events

- **Connect**
  - Automatically validates the JWT token provided in the headers.
  - Example:
    ```javascript
    const socket = io("http://localhost:8000/socket.io", {
      auth: { token: "Bearer <your_jwt_token>" }
    });
    ```

- **Disconnect**
  - Automatically logs when a user disconnects.

#### Chatroom Events

- **`joinRoom`**
  - Joins a chatroom if the user is authenticated and a member of the room.
  - Example:
    ```javascript
    socket.emit("joinRoom", { chatroomId: "<chatroom_id>" });
    ```

- **`leaveRoom`**
  - Leaves a chatroom.
  - Example:
    ```javascript
    socket.emit("leaveRoom", { chatroomId: "<chatroom_id>" });
    ```

#### Messaging Events

- **`chatroomMessage`**
  - Sends a message to a chatroom.
  - Example:
    ```javascript
    socket.emit("chatroomMessage", {
      chatroomId: "<chatroom_id>",
      message: "Hello World!"
    });
    ```

- **`newMessage`**
  - Broadcasts a new message to all users in the chatroom.

---

## Testing the Application

### Using Postman

1. Import the API collection and environment (if provided).
2. Use the `/api/user/login` endpoint to get your JWT token.
3. Add the `Authorization` header (`Bearer <token>`) to test protected routes.

### Using Socket.IO

1. Use a Socket.IO client library or Postman WebSocket feature.
2. Provide the token as part of the connection headers:
    ```javascript
    const socket = io("http://localhost:8000", {
      auth: { token: "Bearer <your_jwt_token>" }
    });
    ```

---

## Project Structure

```bash
├── app
│   ├── server
│   │   ├── database.py        # MongoDB connection
│   │   ├── routes             # API routes for user, chatroom, and messages
│   │   ├── models             # Pydantic models for validation
│   │   └── app.py             # Main application entry point
├── requirements.txt           # Python dependencies
├── README.md                  # Application documentation
├── .env                       # Environment variables
