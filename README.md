# Facilitator Gym

A multi-party difficult conversation simulator for training facilitators. This project uses AI agents to simulate participants in a conversation, allowing a human facilitator to practice intervention techniques.

## Architecture

- **Backend**: Python (FastAPI) - Manages session state, branching, and AI agents.
- **Frontend**: TypeScript (Next.js) - Real-time UI for the facilitator using LiveKit.
- **Real-time Communication**: LiveKit - Handles audio streaming and data messaging.
- **Workers**: Python (LiveKit Agents) - `Conductor` manages the room state, `SpeakerWorker` handles agent speech, and `TranscriptionWorker` handles STT.
- **Database**: MongoDB - Stores case studies, session logs, and version control trees.

## Project Structure

### Root

- `app/`: Backend Python code (FastAPI).
- `frontend/`: Frontend Next.js code.
- `tests/`: Backend tests.
- `.env.local`: Environment variables (shared).

### Backend (`app/`)

The core logic of the simulator, built with FastAPI.

#### `app/api/` (Route Handlers)

- `case_studies.py`: Endpoints for creating and retrieving case studies (the "templates" for simulations).
- `sessions.py`: Endpoints for starting new sessions and managing session state.
- `branches.py`: Endpoints for version control (listing branches, setting active branch).
- `intervene.py`: The core intervention endpoint. Handles forking the conversation and inserting the facilitator's speech.
- `rewind.py`: Endpoints for setting the playhead to a previous state for replay.
- `transcripts.py`: Endpoints to fetch the linear transcript of a specific branch (resolving inheritance).
- `metrics.py`: Endpoints to retrieve conversation metrics (e.g., speaking time).
- `livekit.py`: Endpoints for issuing LiveKit access tokens for users and agents.
- `utterances.py`: Internal endpoints for appending utterances (used by Conductor).
- `checkpoints.py`: Endpoints for listing state checkpoints.

#### `app/core/` (Configuration)

- `config.py`: Pydantic settings model. Loads environment variables from `.env.local`.
- `logging.py`: Logging configuration.

#### `app/db/` (Database)

- `mongo.py`: Initializes the asynchronous MongoDB client (`motor`).
- `repos/`: Data Access Objects (DAOs) for interacting with MongoDB collections.
  - `base.py`: Abstract base repository with common CRUD operations.
  - `case_study.py`, `session.py`, `branch.py`, `utterance.py`, `checkpoint.py`, `metrics.py`: Specific repositories for each domain entity.

#### `app/domain/` (Business Logic)

- `schemas.py`: Pydantic models defining the data structure for API requests, responses, and DB documents.
- `services/`: Complex domain logic.
  - `session_manager.py`: Logic for initializing sessions and cloning seed utterances.
  - `version_control.py`: Logic for branching, forking, and managing the conversation tree.
  - `transcript_resolver.py`: Logic to traverse the branch history and reconstruct a linear transcript.
  - `conductor_writer.py`: Handles atomic writes of utterances and checkpoints.
  - `checkpointing.py`: Manages creation of state snapshots.

#### `app/livekit/` (Real-time Runtime)

- `conductor.py`: The "Room Manager". Connects to LiveKit, manages the floor (who speaks), handles bids, and captures completed turns to the DB.
- `speaker_worker.py`: Represents an AI participant. Connects to LiveKit, holds a persona, bids for the floor, and simulates speech.
- `protocol.py`: Definitions for data messages exchanged between Conductor, Agents, and Frontend.
- `tokens.py`: Helper utilities for generating LiveKit JWTs.

#### `app/metrics/` (Analysis)

- `engine.py`: Computes metrics like speaking time distribution based on the transcript history.

#### Root Files

- `main.py`: The entry point for the FastAPI application. Configures routes and middleware.

---

### Frontend (`frontend/`)

The facilitator's dashboard, built with Next.js (App Router).

#### `frontend/src/app/` (Pages)

- `page.tsx`: The main simulation interface. Handles:
  - Session initialization.
  - LiveKit connection.
  - Rendering the participant grid.
  - Capturing microphone input for interventions.
- `layout.tsx`: Global layout and font configuration.
- `globals.css`: Global Tailwind CSS styles.

#### `frontend/src/components/` (UI Components)

- `ParticipantGrid.tsx`: Layout container for participant tiles.
- `ParticipantTile.tsx`: Individual card for a participant/agent. Shows avatar, name, and speaking status.
- `ControlBar.tsx`: Bottom bar with controls for Play/Pause (Start Session) and Microphone (Intervene).
- `DashboardPanel.tsx`: Side panel displaying metrics (e.g., tension, speaking time).

#### `frontend/src/hooks/` (Logic)

- `useLiveKit.ts`: A custom React hook that encapsulates all LiveKit logic. It manages the `Room` connection, tracks participants, and handles audio track subscriptions.

#### `frontend/src/lib/` (Utilities)

- `api.ts`: A strongly-typed client for calling the backend API endpoints (e.g., `startSession`, `intervene`).

#### Configuration Files

- `package.json`: Node.js dependencies and scripts.
- `tsconfig.json`: TypeScript configuration.
- `tailwind.config.ts`: Tailwind CSS configuration.
- `next.config.ts`: Next.js configuration.

## Prerequisites

- **Python 3.10+** (Strictly required due to `TypeAlias` and `|` union syntax in dependencies)
- **Node.js 18+**
- **MongoDB**
- **LiveKit Server**
- **LiveKit Agents & Plugins** (Installed via requirements.txt)
- **ffmpeg** (Required for audio playback)
  - Mac: `brew install ffmpeg`
  - Linux: `sudo apt-get install ffmpeg`

## Setup

### 1. Environment Variables

Create a `.env.local` file in the root directory:

```env
# Database
MONGO_URI=mongodb://localhost:27017
MONGO_DB=facilitator_gym

# LiveKit
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

Copy this file to `frontend/.env.local` as well if needed (Next.js automatically loads it from root in some configs, but safer to copy).

### 2. Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### 1. Start the Backend

```bash
# From root
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

The API docs will be available at `http://localhost:8000/docs`.

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`.

## Testing

Run the backend test suite:

```bash
# Run all tests
PYTHONPATH=. pytest

# Run E2E integration test
PYTHONPATH=. pytest tests/test_e2e.py
```

## Usage Flow

1.  **Start Session**: Click "Start Session" on the frontend. This calls the backend to initialize a new session and create a root branch.
2.  **LiveKit Connection**: The frontend connects to the LiveKit room.
3.  **Simulation**: The backend spawns a `Conductor` (to manage state) and multiple `SpeakerWorker` instances (one for each persona) which join the LiveKit room.
4.  **Intervention**: Speak into the microphone to intervene. The `TranscriptionWorker` captures your speech, the `Conductor` forks the conversation state, and allows you to steer the direction.
