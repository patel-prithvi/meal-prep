import matplotlib.pyplot as plt
from io import BytesIO
from meal_service import save_nutrition_chart

def generate_daily_nutrition_chart(final_meal, user_id):
    total_fat = 0
    total_carbs = 0
    total_protein = 0
    for day in final_meal.values():
        for meal in day.values():
            total_fat += meal.get("fat", 0)
            total_carbs += meal.get("carbs", 0)
            total_protein += meal.get("protein", 0)

    labels = [
        "Fat",
        "Carbs",
        "Protein"
    ]

    values = [
        total_fat,
        total_carbs,
        total_protein
    ]

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=140)
    ax.set_title("Daily Nutrition Intake")

    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close(fig)

    buf.seek(0)
    raw_byte = buf.getvalue()
    print("Chart Generated successfully")
    print(type(raw_byte))
    save_nutrition_chart(raw_byte, user_id)
    return raw_byte  # RETURN RAW BYTE