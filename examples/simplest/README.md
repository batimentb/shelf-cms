Simplest application possible
====

Here we create an admin to manage posts in a blog.  
Data will be stored in a SQLite file.  
Passwords will be stored in plain text (and you should never do that).  

1. Install dependancies
```pip install shelfcms```

2. Launch simplest.py
```python simplest.py```

3. Create a user in the database
```sqlite3 simplest.db```
```INSERT into user (email, password, active, confirmed_at) VALUES ("admin@shelfcms.com", "password", 1, datetime());```

4. Give your user superadmin permission
```INSERT INTO roles_users (user_id, role_id) VALUES (1, 2);```

5. In a browser, go to http://localhost:5000/admin/
Log using your credentials ( admin@shelfcms.com / password )
