Blog application
====

Here we create an admin to manage posts in a blog.  
Posts have four columns: title, content, picture and state.  
Three plugins will be used: workflow, library and wysiwyg.  
Data will be stored in a SQLite file.  
Password hashes will be stored (bcrypt function).  

1. Install dependancies  
```pip install shelfcms```

2. Create static/ directory  
```mkdir static```

2. Launch app.py  
```python app.py```

3. In a browser, go to http://localhost:5000/admin/ and create your account by clicking the registration link

4. Give your user superadmin, reviewer and publisher permissions  
```INSERT INTO roles_users (user_id, role_id) VALUES (1, 2),(1,3),(1,4);```

5. In a browser, go to http://localhost:5000/admin/   
Login using your chosen credentials
