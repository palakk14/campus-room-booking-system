from flask import render_template, request, redirect, session, flash
from app import app
from db import get_db_connection

@app.route('/rooms')
def rooms():
    if 'user_id' not in session:
        return redirect('/login')

    search = request.args.get('search', '')
    room_type = request.args.get('type', '')
    capacity = request.args.get('capacity', '')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    query = "SELECT * FROM rooms WHERE 1=1"
    values = []

    if search:
        query += " AND room_name LIKE %s"
        values.append(f"%{search}%")

    if room_type:
        query += " AND type=%s"
        values.append(room_type)

    if capacity:
        query += " AND capacity >= %s"
        values.append(capacity)

    query += " ORDER BY room_name"

    cur.execute(query, values)
    rooms = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("rooms.html", rooms=rooms)



@app.route('/book/<int:room_id>', methods=['GET', 'POST'])
def book_room(room_id):
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        purpose = request.form['purpose']

        if end_time <= start_time:
            flash("End time must be after start time")
            return redirect(f'/book/{room_id}')

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT * FROM bookings
            WHERE room_id=%s
            AND date=%s
            AND status='Booked'
            AND (%s < end_time AND %s > start_time)
        """, (room_id, date, start_time, end_time))

        conflict = cur.fetchone()

        if conflict:
            cur.close()
            conn.close()
            flash("Room already booked for this time slot")
            return redirect(f'/book/{room_id}')

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bookings
            (user_id, room_id, date, start_time, end_time, purpose, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            session['user_id'],
            room_id,
            date,
            start_time,
            end_time,
            purpose,
            'Booked'
        ))

        conn.commit()
        cur.close()
        conn.close()

        flash("Booking successful")
        return redirect('/mybookings')

    return render_template("book_room.html", room_id=room_id)


@app.route('/mybookings')
def mybookings():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT bookings.*, rooms.room_name
        FROM bookings
        JOIN rooms ON bookings.room_id = rooms.room_id
        WHERE bookings.user_id=%s
    """, (session['user_id'],))

    bookings = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("mybookings.html", bookings=bookings)


@app.route('/cancel/<int:booking_id>')
def cancel_booking(booking_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM bookings
        WHERE booking_id=%s AND user_id=%s
    """, (booking_id, session['user_id']))

    conn.commit()

    cur.close()
    conn.close()

    flash("Booking cancelled")
    return redirect('/mybookings')

@app.route('/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
def edit_booking(booking_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Get only user's own booking
    cur.execute("""
        SELECT * FROM bookings
        WHERE booking_id=%s AND user_id=%s
    """, (booking_id, session['user_id']))

    booking = cur.fetchone()

    if not booking:
        cur.close()
        conn.close()
        return redirect('/mybookings')

    if request.method == 'POST':
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        purpose = request.form['purpose']

        if end_time <= start_time:
            flash("End time must be after start time", "danger")
            return redirect(f'/edit_booking/{booking_id}')

        # Conflict check excluding current booking
        cur.execute("""
            SELECT * FROM bookings
            WHERE room_id=%s
            AND date=%s
            AND booking_id != %s
            AND status='Booked'
            AND (%s < end_time AND %s > start_time)
        """, (
            booking['room_id'],
            date,
            booking_id,
            start_time,
            end_time
        ))

        conflict = cur.fetchone()

        if conflict:
            cur.close()
            conn.close()
            flash("Room already booked for this time slot", "danger")
            return redirect(f'/edit_booking/{booking_id}')

        cur = conn.cursor()
        cur.execute("""
            UPDATE bookings
            SET date=%s,
                start_time=%s,
                end_time=%s,
                purpose=%s
            WHERE booking_id=%s
        """, (
            date,
            start_time,
            end_time,
            purpose,
            booking_id
        ))

        conn.commit()
        cur.close()
        conn.close()

        flash("Booking updated successfully", "success")
        return redirect('/mybookings')

    cur.close()
    conn.close()

    return render_template("edit_booking.html", booking=booking)