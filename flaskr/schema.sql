DROP TABLE IF EXISTS entries;

CREATE TABLE entries (
    id integer primary key autoincrement,
    title text not null,
    'text' text not null
);

DROP TABLE IF EXISTS replies;

CREATE TABLE replies (
     id integer PRIMARY KEY autoincrement,
     'reply' text not null,
     entry_id int,
     FOREIGN KEY (entry_id) REFERENCES entries(id)
);

DROP TABLE IF EXISTS user_data;

CREATE TABLE user_data (
    id integer PRIMARY KEY autoincrement,
    'name' text not null,
    'email' text not null
);

DROP TABLE IF EXISTS user_diploma;

CREATE TABLE user_diploma (
    'id' text not null,
    'school' text not null,
    'year' text,
    user_id int,
    FOREIGN KEY (user_id) REFERENCES user_data(id)
);

DROP TABLE IF EXISTS user_experiences;

CREATE TABLE user_experiences (
    'id' text not null,
    'title' text not null,
    'corporation' text not null,
    'location' text,
    'year' text,
    user_id int,
    FOREIGN KEY (user_id) REFERENCES user_data(id)
)

