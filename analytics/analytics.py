from flask import render_template, session, redirect, jsonify
from app import app
from db import get_db_connection
from security.security import admin_required


# ─────────────────────────────────────────────
# ANALYTICS DASHBOARD  (admin only)
# ─────────────────────────────────────────────

@app.route("/analytics")
@admin_required
def analytics():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Total bookings per room (top 5)
    cur.execute("""
        SELECT r.room_name, COUNT(b.booking_id) AS total
        FROM bookings b
        JOIN rooms r ON b.room_id = r.room_id
        GROUP BY r.room_id
        ORDER BY total DESC
        LIMIT 5
    """)
    top_rooms = cur.fetchall()

    # Bookings per day (last 14 days)
    cur.execute("""
        SELECT DATE(date) AS day, COUNT(*) AS total
        FROM bookings
        WHERE date >= CURDATE() - INTERVAL 14 DAY
        GROUP BY day
        ORDER BY day
    """)
    daily_trend = cur.fetchall()

    # Peak booking hours
    cur.execute("""
        SELECT HOUR(start_time) AS hour, COUNT(*) AS total
        FROM bookings
        GROUP BY hour
        ORDER BY hour
    """)
    peak_hours = cur.fetchall()

    # Booking status breakdown
    cur.execute("""
        SELECT status, COUNT(*) AS total
        FROM bookings
        GROUP BY status
    """)
    status_breakdown = cur.fetchall()

    # Most active users (top 5)
    cur.execute("""
        SELECT u.name, COUNT(b.booking_id) AS total
        FROM bookings b
        JOIN users u ON b.user_id = u.user_id
        GROUP BY b.user_id
        ORDER BY total DESC
        LIMIT 5
    """)
    top_users = cur.fetchall()

    # Overall summary numbers
    cur.execute("SELECT COUNT(*) AS c FROM bookings")
    total_bookings = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM users")
    total_users = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM rooms WHERE status='Available'")
    available_rooms = cur.fetchone()["c"]

    cur.close()
    conn.close()

    return render_template(
        "analytics.html",
        top_rooms=top_rooms,
        daily_trend=daily_trend,
        peak_hours=peak_hours,
        status_breakdown=status_breakdown,
        top_users=top_users,
        total_bookings=total_bookings,
        total_users=total_users,
        available_rooms=available_rooms,
    )


# ─────────────────────────────────────────────
# JSON API ENDPOINTS  (for Chart.js)
# ─────────────────────────────────────────────

@app.route("/analytics/api/daily")
@admin_required
def api_daily():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT DATE_FORMAT(date, '%d %b') AS day, COUNT(*) AS total
        FROM bookings
        WHERE date >= CURDATE() - INTERVAL 14 DAY
        GROUP BY day
        ORDER BY date
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)


@app.route("/analytics/api/rooms")
@admin_required
def api_rooms():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT r.room_name, COUNT(b.booking_id) AS total
        FROM bookings b
        JOIN rooms r ON b.room_id = r.room_id
        GROUP BY r.room_id
        ORDER BY total DESC
        LIMIT 8
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)


@app.route("/analytics/api/peak")
@admin_required
def api_peak():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT HOUR(start_time) AS hour, COUNT(*) AS total
        FROM bookings
        GROUP BY hour
        ORDER BY hour
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)
