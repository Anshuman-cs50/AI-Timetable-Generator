# AI Timetable Generator

A powerful, automatic timetable generation system built with **Flask** and **Google OR-Tools**. This application uses advanced Constraint Satisfaction Problem (CSP) techniques to solve complex scheduling conflicts for educational institutions.

## 🚀 Features

- **Automated AI Scheduling**: Uses the CP-SAT solver to generate optimized timetables based on room capacity, faculty availability, and student group constraints.
- **Hierarchical Data Management**:
  - Manage **Departments** and **Courses**.
  - Track **Student Groups** and their specific capacities.
  - Profile **Faculty Members** with weekly hour limits.
  - Catalog **Subjects** (Theory vs. Lab) and assign them to specific instructors.
- **Universal CSV Import**: 
  - Drag-and-drop CSV upload for all data entities.
  - Interactive **Preview & Edit** table to fix data typos before final ingestion.
  - Real-time column validation and mapping.
- **Smart Constraint Analysis**: Provides feedback on "Possible Bottlenecks" if a valid schedule cannot be found (e.g., room shortages or faculty overlaps).
- **Responsive & Premium UI**: A modern dashboard with smooth animations, dark-mode elements, and glassmorphism-inspired design.

## 🛠️ Tech Stack

- **Backend**: Python, Flask, SQLAlchemy (SQLite/Postgres)
- **AI Solver**: Google OR-Tools (CP-SAT)
- **Frontend**: HTML5, Vanilla CSS, JavaScript (jQuery)
- **Authentication**: Flask-Login

## 📦 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Anshuman-cs50/AI-Timetable-Generator.git
   cd AI-Timetable-Generator
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the Database**:
   ```bash
   # The application will automatically create instance/timetable.db on first run
   python run.py
   ```

5. **Access the App**:
   Open `http://127.0.0.1:5000` in your browser.

## 📋 Usage Guide

1. **Data Onboarding**: Start by adding your **Departments** and **Courses** in the **Architecture** tab.
2. **Setup Groups & Faculty**: Add **Student Groups** to your courses and **Faculty Members** to your departments.
3. **Define Subjects**: Create a subject catalog, specifying if it's a "Lab" or "Theory" and assigning the appropriate faculty.
4. **Generate**: Go to the **Generate** tab and hit the computation button. The AI will take approximately 30 seconds to arrive at an optimal solution.
5. **View Timetable**: Once generated, view the full weekly grid in the **Timetable** section.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---
*Built with ❤️ for educational efficiency.*
