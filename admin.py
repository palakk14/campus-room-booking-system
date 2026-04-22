from flask import render_template, session, redirect
from app import app
from db import get_db_connection


@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        return redirect('/dashboard')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT bookings.*, users.name, rooms.room_name
        FROM bookings
        JOIN users ON bookings.user_id = users.user_id
        JOIN rooms ON bookings.room_id = rooms.room_id
        ORDER BY booking_id DESC
    """)

    bookings = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin.html", bookings=bookings)