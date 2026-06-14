# 🍽️ Meal Prep - A Meal Planner
### Personalized Meal Planning & Nutrition Analysis Web Application

Meal Prep is a Flask-based web application that generates customised meal plans based on user health details and fitness goals. It calculates daily calorie requirements, distributes macronutrients, and provides structured meal recommendations along with nutrition visualisation.

---

## 🚀 Features

### 👤 User Features
- User Registration & Login
- Secure password hashing (no plain-text storage)
- Goal-based meal planning (Weight Loss / Gain / Maintenance)
- Calorie calculation using BMR formula
- Macro-nutrient distribution (Protein, Carbs, Fats)
- Nutrition charts & analysis
- AI-powered daily health tips
- Dark mode support
- Responsive UI

---

### 🔐 Security
- Password hashing for secure storage
- Session-based authentication
- Protected routes for authorized users

---

### 🛠 Admin Panel
- View registered users
- Monitor generated meal plans
- Manage user data
- Basic administrative control system

---

## 🧠 How It Works

1. User registers and logs in  
2. Enters personal details (age, weight, height, goal)  
3. System calculates BMR  
4. Adjusts calories based on fitness goal  
5. Distributes macronutrients  
6. Generates structured meal plan  
7. Displays nutrition breakdown with charts  

---

## 🏗️ Project Architecture

Meal Prep follows a modular service-layer architecture:
```text
Meal-Prep/
├── app.py              # Main application entry point
├── auth.py             # Authentication logic
├── db.py               # Database operations
├── meal_service.py     # Core meal logic
├── meal_plan.py        # Meal plan generation
├── ai_service.py       # AI health tips
├── nutrition_chart.py  # Chart generation
├── admin_service.py    # Admin functionalities
├── templates/          # HTML templates
└── static/             # CSS, JS, assets
```
---

## 🛠 Tech Stack

- Python
- Flask
- Postgresql
- HTML
- CSS
- JavaScript
- Bootstrap

---

## ⚡ Setup Instructions  

### 1. Clone the Repository  
```bash
git clone https://github.com/patel-prithvi/Meal-Prep.git
cd Meal-Prep
```

### 2. Create virtual environment
```bash
python -m venv venv
```

### 3. python -m venv venv
**Windows:**
```bash
venv\Scripts\activate
```
**Mac/Linux:**
```bash
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the application
```bash
python app.py
```

---

### 📈 Future Enhancements
- JWT authentication
- Weekly analytics dashboard
- PDF export of meal plans
- Cloud deployment (AWS / Render)
- Food database API integration
- User progress tracking

---

### 🎯 Learning Outcomes
This project helped me understand:
- Backend architecture design
- Business logic separation
- Secure authentication implementation
- Database structuring
- Real-world application workflow design

---

### 🤝 Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss improvements.

---

### 📬 Contact
If you have feedback or suggestions, feel free to connect on LinkedIn.
