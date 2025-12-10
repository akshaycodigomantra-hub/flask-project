from db import db

# ================================
# USER CRUD (RAW SQL)
# ================================

def create_user(name, email, password):
    sql = """
        INSERT INTO users (name, email, password)
        VALUES (:name, :email, :password)
        RETURNING id
    """
    result = db.session.execute(sql, {
        "name": name, 
        "email": email, 
        "password": password
    })
    db.session.commit()
    return result.fetchone()[0]


def get_all_users():
    sql = "SELECT * FROM users ORDER BY id DESC"
    result = db.session.execute(sql)
    return result.fetchall()


def update_user(user_id, name, email):
    sql = """
        UPDATE users
        SET name = :name, email = :email
        WHERE id = :id
    """
    db.session.execute(sql, {"id": user_id, "name": name, "email": email})
    db.session.commit()


def delete_user(user_id):
    sql = "DELETE FROM users WHERE id = :id"
    db.session.execute(sql, {"id": user_id})
    db.session.commit()



# ================================
# MODULE CRUD (RAW SQL)
# ================================

def create_module(title, description, sequence):
    sql = """
        INSERT INTO modules (title, description, sequence)
        VALUES (:title, :description, :sequence)
        RETURNING id
    """
    result = db.session.execute(sql, {
        "title": title,
        "description": description,
        "sequence": sequence
    })
    db.session.commit()
    return result.fetchone()[0]


def get_paginated_modules(page, limit):
    offset = (page - 1) * limit

    sql = """
        SELECT * FROM modules
        ORDER BY sequence ASC
        LIMIT :limit OFFSET :offset
    """
    result = db.session.execute(sql, {"limit": limit, "offset": offset})
    return result.fetchall()


def update_module(module_id, title, description):
    sql = """
        UPDATE modules
        SET title = :title, description = :description
        WHERE id = :id
    """
    db.session.execute(sql, {"id": module_id, "title": title, "description": description})
    db.session.commit()


def delete_module(module_id):
    sql = "DELETE FROM modules WHERE id = :id"
    db.session.execute(sql, {"id": module_id})
    db.session.commit()



# ================================
# BLOG CRUD (RAW SQL)
# ================================

def create_blog(title, content, author):
    sql = """
        INSERT INTO blogs (title, content, author)
        VALUES (:title, :content, :author)
        RETURNING id
    """
    result = db.session.execute(sql, {
        "title": title,
        "content": content,
        "author": author
    })
    db.session.commit()
    return result.fetchone()[0]


def get_all_blogs():
    sql = "SELECT * FROM blogs ORDER BY id DESC"
    result = db.session.execute(sql)
    return result.fetchall()


def update_blog(blog_id, title, content):
    sql = """
        UPDATE blogs
        SET title = :title, content = :content
        WHERE id = :id
    """
    db.session.execute(sql, {"id": blog_id, "title": title, "content": content})
    db.session.commit()


def delete_blog(blog_id):
    sql = "DELETE FROM blogs WHERE id = :id"
    db.session.execute(sql, {"id": blog_id})
    db.session.commit()
