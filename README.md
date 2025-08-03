# AlignExercise: AI Fitness Trainer

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/MANOJ1245723/AlignExercise)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AlignExercise is a full-stack web application that acts as your personal AI fitness coach. It uses your computer's webcam and real-time pose estimation to guide you through exercises, count your repetitions automatically, and provide live feedback on your form. Workout plans are dynamically generated and tailored to your personal biometrics (age, BMI) and progress.


## Key Features

*   **Real-time Repetition Counting:** Uses Google's MediaPipe Pose model to automatically count pushups, squats, and situps.
*   **Personalized Workout Plans:** Generates daily exercise plans based on the user's BMI, age, and current progress.
*   **Live Form Correction:** Provides real-time feedback like "Keep your back straight!" to help prevent injury and ensure proper technique.
*   **Progress Tracking:** Saves user performance, calculates a completion percentage, and advances the user to the next "day" upon completion.
*   **Secure User Authentication:** Robust user registration and login system with password hashing and session management.
*   **Audio Feedback:** Uses the Web Speech API to provide audio cues, announcing the rep count as it happens.

## Tech Stack

*   **Backend:** Python, Flask, Gunicorn
*   **Database:** Postgresql
*   **Frontend:** HTML5, CSS3, JavaScript
*   **Computer Vision:** Google MediaPipe Pose
*   **Containerization:** Docker, Docker Compose

---

## 🚀 Getting Started with Docker

Thanks to Docker, you can get AlignExercise running with just **one command**. The entire setup, including the database and its initial tables, is fully automated.

### Step 1: Clone the Repository

```bash
git clone https://github.com/MANOJ1245723/AlignExercise.git
cd AlignExercise
```
### Step 2: Run with Docker Compose
This single command will build the necessary Docker images, start the web application and the database, and automatically initialize the database tables.
```bash
docker compose up --build
```
### Step 3: Open your browser
Open AlignExercise: http://localhost:8080
