import os
from dotenv import load_dotenv
from google import genai

from ai_service import generate_health_tip

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)

from functools import wraps
from flask import (
    Flask, render_template, request,
    redirect, session, flash
)
from flask_mail import Mail, Message
from auth import create_user, authenticate_user_with_role, get_user, get_user_name, user_exists
from db import get_connection
from werkzeug.security import generate_password_hash
from meal_plan import generate_7_day_meal_plan
from nutrition_chart import generate_daily_nutrition_chart
from meal_service import get_meal_plan, get_published_blogs
from admin_service import get_admin_stats, get_all_users_with_details, get_active_meal_plans, get_all_meal_plans
from datetime import date, datetime
from flask import abort
import random
import base64

def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good Morning"
    elif hour < 17:
        return "Good Afternoon"
    else:
        return "Good Evening"

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            return redirect("/dashboard")
        return f(*args, **kwargs)
    return wrapper

app = Flask(__name__)
app.secret_key = "super_secret_key"   # move to .env later

# ---------------- MAIL CONFIG ----------------
app.config['MAIL_SERVER'] = 'smtp-relay.brevo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_DEFAULT_SENDER'] = (
    'Meal Prep',
    os.getenv("MAIL_USERNAME")
)

app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")

# IMPORTANT
app.config['MAIL_TIMEOUT'] = 15

mail = Mail(app)


mail = Mail(app)

# ---------------- LANDING ----------------
@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/auth", methods=["GET"])
def auth():
    mode = request.args.get("mode", "login")  # login | signup
    return render_template("auth.html", mode=mode)

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.form.to_dict()

    if data["password"] != data["confirm_password"]:
        flash("Passwords do not match", "danger")
        return redirect("/auth?mode=signup")
    
    exiting= user_exists(data["email"])
    if exiting != None:
        if exiting[1]:
            flash("An account with this email already exists.", "danger")
            return redirect("/auth?mode=login")
        else:
            flash("This account is disabled. Please contact support.", "danger")
            return redirect("/auth?mode=signup")

    # otp = random.randint(100000, 999999)

    session["signup_data"] = data
    # session["otp"] = otp

    # msg = Message(
    #     subject="Your Meal Prep Verification Code",
    #     recipients=[data["email"]],
    # )
        
    # msg.body = f"""
    #     Hello,

    #     Your verification code is: {otp}

    #     If you did not request this, please ignore this email.

    #     – Meal Prep Team
    # """

    #  mail.send(msg)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email=%s", (data["email"],))
    if cur.fetchone():
        flash("Email already registered. Please login.", "info")
        session.clear()
        return redirect("/auth?mode=login")

    user_id = create_user(data)
    session.clear()
    session["user_id"] = user_id

    flash("OTP sent to your email", "success")
    # return redirect("/verify-otp")
    return redirect("/mealplan")

# ---------------- VERIFY OTP ----------------
# @app.route("/verify-otp", methods=["GET", "POST"])
# def verify_otp():
#     if "signup_data" not in session:
#         return redirect("/auth?mode=signup")

#     if request.method == "POST":
#         user_otp = request.form.get("otp")

#         if not user_otp:
#             flash("Please enter OTP", "danger")
#             return redirect("/verify-otp")

#         if int(user_otp) == session["otp"]:
#             data = session["signup_data"]

#             conn = get_connection()
#             cur = conn.cursor()
#             cur.execute("SELECT id FROM users WHERE email=%s", (data["email"],))
#             if cur.fetchone():
#                 flash("Email already registered. Please login.", "info")
#                 session.clear()
#                 return redirect("/auth?mode=login")

#             user_id = create_user(data)
#             msg = Message(
#                 subject="🎉 Welcome to Meal Planner!",
#                 recipients=[data["email"]]
#             )

#             msg.html = f"""
#             <html>
#             <body style="font-family: Arial; padding:20px;">
#                 <h2 style="color:#4B5320;">Welcome {data['name']}! 🥗</h2>
#                 <p>Your email has been successfully verified.</p>
#                 <p>You can now generate personalized meal plans.</p>
#                 <br>
#                 <p>— Team Meal Planner</p>
#             </body>
#             </html>
#             """

#             mail.send(msg)

#             session.clear()
#             session["user_id"] = user_id
#             flash("Account verified successfully!", "success")
#             return redirect("/mealplan")

#         flash("Invalid OTP", "danger")

#     return render_template("verify_otp.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = authenticate_user_with_role(email, password)
        if user == "DISABLED":
            flash("Your account has been disabled by admin", "danger")
            return redirect("/auth?mode=login")
        
        if not user:
            flash("Invalid email or password", "danger")
            return redirect("/auth?mode=login")

        session["user_id"] = user["id"]
        session["role"] = user["role"]

        # Redirect admin separately
        if user["role"] == "admin":
            return redirect("/admin")

        return redirect("/dashboard")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    stats = get_admin_stats()

    return render_template(
        "admin/admin_dashboard.html",
        stats=stats
    )

# ---------------- ADMIN USERS ----------------
@app.route("/admin/users")
def admin_users():
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    users, plans = get_all_users_with_details()
    return render_template("admin/admin_users.html", users=users, plans=plans)

@app.route("/admin/users/<int:user_id>/deactivate")
def deactivate_user(user_id):
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active=FALSE WHERE id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/users")


@app.route("/admin/users/<int:user_id>/activate")
def activate_user(user_id):
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active=TRUE WHERE id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/users")


@app.route("/admin/users/<int:user_id>/delete")
def delete_user(user_id):
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM meal_plans WHERE user_id=%s", (user_id,))
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/users")

# ---------------- ADMIN MEAL PLANS ----------------
@app.route("/admin/meal-plans")
def admin_meal_plans():
    if "user_id" not in session:
        return redirect("/auth?mode=login")
    
    filter_type = request.args.get("filter", "all")

    if filter_type == "active":
        plans = get_active_meal_plans()
    else:
        plans = get_all_meal_plans()

    return render_template(
        "admin/admin_meal_plans.html",
        plans=plans,
        filter=filter_type,
        today=date.today()
    )

@app.route("/admin/meal-plans/<int:plan_id>/invalidate")
def invalidate_meal_plan(plan_id):
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE meal_plans
        SET is_active = FALSE, end_plan_date = CURRENT_DATE - INTERVAL '1 day'
        WHERE plan_id = %s
    """, (plan_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/meal-plans?filter=active")

# ---------------- ADMIN Blogs ----------------
@app.route("/admin/blogs")
def admin_blogs():
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, category, is_published, created_at
        FROM blogs
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    blogs = []
    for b in rows:
        blogs.append({
            "id": b[0],
            "title": b[1],
            "category": b[2],
            "is_published": b[3],
            "created_at": b[4]
        })

    return render_template("admin/admin_blogs.html", blogs=blogs)

@app.route("/admin/blogs/new", methods=["GET", "POST"])
def admin_add_blog():
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        summary = request.form["summary"]
        content = request.form["content"]
        is_published = "is_published" in request.form

        slug = title.lower().replace(" ", "-")

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO blogs (title, slug, category, summary, content, is_published)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (title, slug, category, summary, content, is_published))
        conn.commit()
        cur.close()
        conn.close()

        return redirect("/admin/blogs")

    return render_template("admin/admin_blog_form.html")

@app.route("/admin/blogs/<int:blog_id>/edit", methods=["GET", "POST"])
def edit_blog(blog_id):
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute("""
            UPDATE blogs SET
                title = %s,
                summary = %s,
                content = %s,
                category = %s,
                is_published = %s
            WHERE id = %s
        """, (
            request.form["title"],
            request.form["summary"],
            request.form["content"],
            request.form["category"],
            bool(request.form.get("is_published")),
            blog_id
        ))

        conn.commit()
        cur.close()
        conn.close()

        flash("Blog updated successfully", "success")
        return redirect("/admin/blogs")

    # GET (load blog data)
    cur.execute("SELECT * FROM blogs WHERE id=%s", (blog_id,))
    blog = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("admin/admin_edit_blog.html", blog=blog)

@app.route("/admin/blogs/<int:blog_id>/delete")
def delete_blog(blog_id):
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM blogs WHERE id=%s", (blog_id,))
    conn.commit()

    cur.close()
    conn.close()

    flash("Blog deleted successfully", "danger")
    return redirect("/admin/blogs")


# ---------------- ADMIN REVIEWS ----------------
@app.route("/admin/reviews")
def admin_reviews():
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT r.id, u.name, u.email, r.rating, r.feedback, r.created_at
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        ORDER BY r.created_at DESC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    reviews = []
    for r in rows:
        reviews.append({
            "id": r[0],
            "name": r[1],
            "email": r[2],
            "rating": r[3],
            "feedback": r[4],
            "created_at": r[5]
        })

    return render_template("admin/admin_reviews.html", reviews=reviews)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    user_id = session["user_id"]
    username = get_user_name(user_id)
    greeting = get_greeting()
    user= get_user(user_id)

    today_date = date.today()
    today = date.today().strftime("%d-%m-%Y")

    plan = get_meal_plan(user_id)

    if not plan:
        return render_template("dashboard.html", username=username, greeting=greeting, no_plan=True)

    end_date = plan["end_date"]
    final_meal = plan["final_meal"]
    daily_calories = plan["daily_calories"] 
    daily_protein = plan["daily_protein"]
    daily_carbs = plan["daily_carbs"]
    daily_fat = plan["daily_fat"]
    
    # Plan expired
    if today_date > end_date:
        return render_template("dashboard.html", username=username, greeting=greeting, plan_expired=True)

    # Get selected day from query param
    selected_day = request.args.get("day", today)
    day_meals = final_meal.get(selected_day)

    # nutrition calculation
    nutrition = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}

    if day_meals:
        for meal in day_meals.values():
            nutrition["calories"] += meal.get("calories", 0)
            nutrition["protein"] += meal.get("protein", 0)
            nutrition["carbs"] += meal.get("carbs", 0)
            nutrition["fat"] += meal.get("fat", 0)

# ---------- PROGRESS INDICATOR ----------
    target_calories = daily_calories
    if nutrition["calories"] <= target_calories:
        progress_status = " 🟢 On Track Today"
    elif nutrition["calories"] <= target_calories + 200:
        progress_status = "🟡 Slightly Above Target"
    else:
        progress_status = "🔴 High Intake Today"

    # ---------- INGREDIENT COLLECTION ----------
    ingredients_list = []
    if day_meals:
        for meal in day_meals.values():
            ing = meal.get("ingredients")
            if ing:
                ingredients_list.append(ing)

    ingredients_text = "\n".join(ingredients_list)

    # ---------- AI HEALTH TIP ----------
    today_key = f"health_tip_{today}"

    if today_key not in session or session[today_key].startswith("Eat balanced"):
        try:
            session[today_key] = generate_health_tip(
                client=client,
                calories=nutrition["calories"],
                protein=nutrition["protein"],
                carbs=nutrition["carbs"],
                fat=nutrition["fat"],
                target_calories= daily_calories,
                target_protein = daily_protein,
                target_carbs = daily_carbs,
                target_fat = daily_fat,
                goal = user["goal"]
            )
        except Exception as e:
            print("Health tip AI error:", e)
            session[today_key] = "Eat balanced meals and stay hydrated today."

    health_tip = session[today_key]

    return render_template(
        "dashboard.html",
        plan_active=True,
        username=username,
        greeting=greeting,
        final_meal=final_meal,
        selected_day=selected_day,
        day_meals=day_meals,
        nutrition=nutrition,
        progress_status=progress_status,
        health_tip=health_tip,
    )

# ---------------- MEAL PLAN PAGE ----------------
@app.route("/mealplan")
def mealplan():
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    user_id = session["user_id"]

    plan = get_meal_plan(user_id)

    if not plan:
        user= get_user(user_id)
        meal_plan= generate_7_day_meal_plan(user,user_id)
        raw_chart = generate_daily_nutrition_chart(meal_plan, user_id)
        print("raw chart : ",type(raw_chart))
        if raw_chart:
            if isinstance(raw_chart, memoryview):
                raw_chart = raw_chart.tobytes()
            chart= base64.b64encode(bytes(raw_chart)).decode("utf-8")
        else:
            chart=None
        return render_template("meal_plan.html", mealplan=meal_plan, nutrition_chart=chart)

    end_date = plan["end_date"]
    final_meal = plan["final_meal"]
    print("raw chart: ", type(plan["chart"]))
    if plan["chart"]:
        if isinstance(plan["chart"], memoryview):
                plan["chart"] = plan["chart"].tobytes()
        nut_chart= base64.b64encode(bytes(plan["chart"])).decode("utf-8")
    else:
        chart=None


    # Plan expired
    if date.today() > end_date:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE meal_plans
            SET is_active = FALSE
            WHERE user_id = %s AND is_active = False
        """, (user_id,))

        conn.commit()
        cur.close()
        conn.close()
        user= get_user(user_id)
        meal_plan= generate_7_day_meal_plan(user,user_id)
        raw_chart = generate_daily_nutrition_chart(meal_plan, user_id)
        print("raw chart : ",type(raw_chart))
        if raw_chart:
            if isinstance(raw_chart, memoryview):
                raw_chart = raw_chart.tobytes()
            chart= base64.b64encode(bytes(raw_chart)).decode("utf-8")
        else:
            chart=None

        return render_template("meal_plan.html", mealplan=meal_plan, nutrition_chart=chart)

    
    return render_template("meal_plan.html", mealplan=final_meal, nutrition_chart=nut_chart)

# ---------------- BLOGS ----------------
@app.route("/blogs")
def blogs():
    category = request.args.get("category")
    blogs = get_published_blogs(category)

    return render_template(
        "blogs.html",
        blogs=blogs,
        selected_category=category
    )

@app.route("/blogs/<int:blog_id>")
def blog_detail(blog_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT title, content, category, created_at
        FROM blogs
        WHERE id=%s AND is_published=TRUE
    """, (blog_id,))

    blog = cur.fetchone()
    cur.close()
    conn.close()

    if not blog:
        abort(404)

    return render_template("blog_detail.html", blog={
        "title": blog[0],
        "content": blog[1],
        "category": blog[2],
        "created_at": blog[3]
    })

# ---------------- REVIEW ----------------
@app.route("/review", methods=["GET", "POST"])
def review():
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    if request.method == "POST":
        rating = request.form.get("rating")
        feedback = request.form.get("feedback")
        user_id = session["user_id"]

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO reviews (user_id, rating, feedback)
            VALUES (%s, %s, %s)
        """, (user_id, rating, feedback))
        conn.commit()
        cur.close()
        conn.close()

        flash("Thank you for your feedback 💚", "success")
        return redirect("/dashboard")

    return render_template("review.html")

# ---------------- PROFILE ----------------
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    user_id = session["user_id"]
    user = get_user(user_id)
    plan = get_meal_plan(user_id)

    needs_new_plan = False

    if request.method == "POST":
        form = request.form

        critical_fields = ["height", "weight", "activity", "goal", "disease", "diet", "allergy"]

        for field in critical_fields:
            if str(user[field]) != str(form[field]):
                needs_new_plan = True
                break

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users SET
                name=%s,
                age=%s,
                gender=%s,
                height=%s,
                weight=%s,
                activity_level=%s,
                goal=%s,
                disease=%s,
                diet_type=%s,
                allergies=%s
            WHERE id=%s
        """, (
            form["name"],
            form["age"],
            form["gender"],
            form["height"],
            form["weight"],
            form["activity"],
            form["goal"],
            form["disease"],
            form["diet"],
            form["allergy"],
            user_id
        ))

        conn.commit()
        cur.close()
        conn.close()

        if needs_new_plan:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("""
                UPDATE meal_plans
                SET is_active = FALSE
                WHERE user_id = %s AND is_active = TRUE
            """, (user_id,))

            conn.commit()
            cur.close()
            conn.close()
            flash("Profile updated. Please generate a new meal plan.", "warning")
            return redirect("/mealplan")

        flash("Profile updated successfully.", "success")
        return redirect("/profile")

    return render_template(
        "profile.html",
        user=user,
        plan=plan,
        today=date.today()
    )

@app.route("/change-password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    user_id = session["user_id"]
    user = get_user(user_id)

    current_password = request.form["current_password"]
    new_password = request.form["new_password"]
    confirm_password = request.form["confirm_password"]

    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect("/profile")

    # 🔐 VERIFY CURRENT PASSWORD
    auth_id = authenticate_user_with_role(user["email"], current_password)
    if not auth_id["id"]:
        flash("Current password is incorrect.", "danger")
        return redirect("/profile")

    new_hash = generate_password_hash(new_password)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash=%s WHERE id=%s",
        (new_hash, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    session.clear()  # 🔥 force logout
    flash("Password changed successfully. Please log in again.", "success")
    return redirect("/login")

@app.route("/delete-account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect("/auth?mode=login")

    user_id = session["user_id"]
    user = get_user(user_id)
    password = request.form["password"]

    # 🔐 VERIFY PASSWORD
    auth_id = authenticate_user_with_role(user["email"], password)
    if not auth_id["id"]:
        flash("Incorrect password. Account not deleted.", "danger")
        return redirect("/profile")

    conn = get_connection()
    cur = conn.cursor()

    # delete dependent data first
    cur.execute("DELETE FROM meal_plans WHERE user_id=%s", (user_id,))
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))

    conn.commit()
    cur.close()
    conn.close()

    session.clear()
    flash("Your account has been permanently deleted.", "success")
    return redirect("/")

# ---------------- STATIC PAGES ----------------

@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/contact", methods=["GET", "POST"])
def contact_page():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        # Optional: send email
        msg = Message(
            subject="New Contact Form Submission",
            recipients=[os.getenv("MAIL_USERNAME")]
        )

        msg.body = f"""
        Name: {name}
        Email: {email}

        Message:
        {message}
        """

        mail.send(msg)
        flash("Your message has been sent successfully!", "success")
        return redirect("/contact")

    return render_template("contact.html")


@app.route("/privacy")
def privacy_page():
    return render_template("privacy.html")


@app.route("/terms")
def terms_page():
    return render_template("terms.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/auth?mode=login")

@app.context_processor
def inject_year():
    return {
        "current_year": datetime.now().year,
        "is_logged_in": "user_id" in session
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
