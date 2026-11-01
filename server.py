import logging
import os
from http import client
import time
from flask import Flask, request, jsonify, g

app = Flask(__name__)

if not os.path.exists('logs'):
    os.makedirs('logs')

request_counter = 1

request_logger = logging.getLogger('request-logger')
request_logger.setLevel(logging.INFO)

request_file_handler = logging.FileHandler('logs/requests.log')
request_console_handler = logging.StreamHandler()

request_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
request_formatter.default_time_format = '%d-%m-%Y %H:%M:%S'
request_formatter.default_msec_format = '%s.%03d'

request_file_handler.setFormatter(request_formatter)
request_console_handler.setFormatter(request_formatter)

request_logger.addHandler(request_file_handler)
request_logger.addHandler(request_console_handler)

@app.before_request
def before_request_func():
    global request_counter

    g.request_num = request_counter
    request_counter += 1

    g.start_time = time.time()

    msg = f"Incoming request | #{g.request_num} | resource: {request.path} | HTTP Verb {request.method}"
    request_logger.info(f"{msg} | request #{g.request_num}")


@app.after_request
def after_request_func(response):
    duration_ms = int((time.time() - g.start_time) * 1000)

    msg = f"request #{g.request_num} duration: {duration_ms}ms"
    request_logger.debug(f"{msg} | request #{g.request_num}")

    return response

books_logger = logging.getLogger('books-logger')
books_logger.setLevel(logging.INFO)

books_file_handler = logging.FileHandler('logs/books.log')

books_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
books_formatter.default_time_format = '%d-%m-%Y %H:%M:%S'
books_formatter.default_msec_format = '%s.%03d'
books_file_handler.setFormatter(books_formatter)

books_logger.addHandler(books_file_handler)

### 1. Health
@app.route('/books/health', methods=['GET'])
def index():
    return 'OK'

### 2. Create a new Book
books = {}
id_to_book = 1
genres_list = ["SCI_FI", "NOVEL", "HISTORY", "MANGA", "ROMANCE", "PROFESSIONAL"]

@app.route('/book', methods=['POST'])
def create_book():
    global id_to_book

    client_input = request.get_json()

    title = client_input.get('title', '')
    author = client_input.get('author', '')
    price = client_input.get('price', 0)
    year = client_input.get('year', 0)
    genres = client_input.get('genres', [])

    for book in books.values():
        if book['title'].lower() == title.lower():
            error_msg = f"Error: Book with the title [{title}] already exists in the system"
            books_logger.error(f"{error_msg} | request# {g.request_num}")
            return jsonify({"errorMessage": error_msg}), 409

    if year < 1940 or year > 2100:
        error_msg = f"Error: Can't create new Book that its year [{year}] is not in the accepted range [1940 -> 2100]"
        books_logger.error(f"{error_msg} | request #{g.request_num}")
        return jsonify({"errorMessage": error_msg}), 409

    if price <= 0:
        error_msg = "Error: Can't create new Book with negative price"
        books_logger.error(f"{error_msg} | request #{g.request_num}")
        return jsonify({"errorMessage": error_msg}), 409

    info_msg = f"Creating new Book with Title [{title}]"
    books_logger.info(f"{info_msg} | request #{g.request_num}")

    total_existing_books = len(books)
    debug_msg = f"Currently there are {total_existing_books} Books in the system. New Book will be assigned with id {id_to_book}"
    books_logger.debug(f"{debug_msg} | request #{g.request_num}")

    book = {
        "id": id_to_book,
        "title": title,
        "author": author,
        "year": year,
        "price": price,
        "genres": genres
    }

    books[id_to_book] = book
    id_to_book += 1
    return jsonify({"result": id_to_book - 1}), 200

### 3. Get Total Books
@app.route('/books/total', methods=['GET'])
def get_total_books():
    author = request.args.get('author')
    price_bigger_than = request.args.get('price-bigger-than')
    price_less_than = request.args.get('price-less-than')
    year_bigger_than = request.args.get('year-bigger-than')
    year_less_than = request.args.get('year-less-than')
    genres_user = request.args.get('genres')

    try:
        if price_bigger_than is not None: price_bigger_than = int(price_bigger_than)
        if price_less_than is not None: price_less_than = int(price_less_than)
        if year_bigger_than is not None: year_bigger_than = int(year_bigger_than)
        if year_less_than is not None: year_less_than = int(year_less_than)
    except ValueError:
        return jsonify({"errorMessage": "Error: numeric query parameters must be numbers"}), 400

    genres_list_user = None
    if genres_user is not None:
        genres_list_user = genres_user.split(',')
        for genre in genres_list_user:
            if genre not in genres_list:
                return jsonify({"errorMessage": f"Error: Genre [{genre}] does not exist"}), 400

    total_count = 0
    for book in books.values():
        match = True

        if author is not None and book['author'].lower() != author.lower():
            match = False

        if price_bigger_than is not None and book['price'] < price_bigger_than:
            match = False
        if price_less_than is not None and book['price'] > price_less_than:
            match = False

        if year_bigger_than is not None and book['year'] < year_bigger_than:
            match = False
        if year_less_than is not None and book['year'] > year_less_than:
            match = False

        if genres_list_user is not None:
            has_matching_genre = False
            for genre in genres_list_user:
                if genre in book['genres']:
                    has_matching_genre = True
                    break

            if not has_matching_genre:
                match = False

        if match:
            total_count += 1

    info_msg = f"Total Books found for requested filters is {total_count}"
    books_logger.info(f"{info_msg} | request #{g.request_num}")

    return jsonify({"result": total_count}), 200


### 4. Get Books data
@app.route('/books', methods=['GET'])
def get_books_data():
    author = request.args.get('author')
    price_bigger_than = request.args.get('price-bigger-than')
    price_less_than = request.args.get('price-less-than')
    year_bigger_than = request.args.get('year-bigger-than')
    year_less_than = request.args.get('year-less-than')
    genres_user = request.args.get('genres')

    try:
        if price_bigger_than is not None: price_bigger_than = int(price_bigger_than)
        if price_less_than is not None: price_less_than = int(price_less_than)
        if year_bigger_than is not None: year_bigger_than = int(year_bigger_than)
        if year_less_than is not None: year_less_than = int(year_less_than)
    except ValueError:
        return jsonify({"errorMessage": "Error: numeric query parameters must be numbers"}), 400

    genres_list_user = None
    if genres_user is not None:
        genres_list_user = genres_user.split(',')
        for genre in genres_list_user:
            if genre not in genres_list:
                return jsonify({"errorMessage": f"Error: Genre [{genre}] does not exist"}), 400

    books_filtered = []

    for book in books.values():
        match = True

        if author is not None and book['author'].lower() != author.lower():
            match = False

        if price_bigger_than is not None and book['price'] < price_bigger_than:
            match = False
        if price_less_than is not None and book['price'] > price_less_than:
            match = False

        if year_bigger_than is not None and book['year'] < year_bigger_than:
            match = False
        if year_less_than is not None and book['year'] > year_less_than:
            match = False

        if genres_list_user is not None:
            has_matching_genre = False
            for genre in genres_list_user:
                if genre in book['genres']:
                    has_matching_genre = True
                    break

            if not has_matching_genre:
                match = False

        if match:
            books_filtered.append(book)

    books_filtered.sort(key=lambda b: b['title'].lower())

    total_count = len(books_filtered)
    info_msg = f"Total Books found for requested filters is {total_count}"
    books_logger.info(f"{info_msg} | request #{g.request_num}")

    return jsonify({"result": books_filtered}), 200

### 5. Get single-book data
@app.route('/book', methods=['GET'])
def get_single_book_data():
    id = request.args.get('id', type=int)

    if id not in books:
        error_msg = f"Error: no such Book with id {id}"
        books_logger.error(f"{error_msg} | request #{g.request_num}")
        return jsonify({"errorMessage": error_msg}), 404

    debug_msg = f"Fetching book id {id} details"
    books_logger.debug(f"{debug_msg} | request #{g.request_num}")

    return jsonify({"result": books[id]}), 200


### 6. Update book's price
@app.route('/book', methods=['PUT'])
def update_book_data():
    book_id = request.args.get('id', type=int)
    new_price = request.args.get('price', type=int)

    if book_id not in books:
        error_msg = f"Error: no such Book with id {book_id}"
        books_logger.error(f"{error_msg} | request #{g.request_num}")
        return jsonify({"errorMessage": error_msg}), 404

    if new_price is None or new_price <= 0:
        error_msg = f"Error: price update for Book [{book_id}] must be a positive integer"
        books_logger.error(f"{error_msg} | request #{g.request_num}")
        return jsonify({"errorMessage": error_msg}), 409

    info_msg = f"Update Book id [{book_id}] price to {new_price}"
    books_logger.info(f"{info_msg} | request #{g.request_num}")

    original_price = books[book_id]['price']
    book_title = books[book_id]['title']

    debug_msg = f"Book [{book_title}] price change: {original_price} --> {new_price}"
    books_logger.debug(f"{debug_msg} | request #{g.request_num}")

    books[book_id]['price'] = new_price

    return jsonify({"result": original_price}), 200



### 7. Delete Book
@app.route('/book', methods=['DELETE'])
def delete_book():
    book_id = request.args.get('id', type=int)

    if book_id not in books:
        error_msg = f"Error: no such book with id {book_id}"
        books_logger.error(f"{error_msg} | request #{g.request_num}")
        return jsonify({"errorMessage": error_msg}), 404

    book_title = books[book_id]['title']

    info_msg = f"Removing book [{book_title}]"
    books_logger.info(f"{info_msg} | request #{g.request_num}")

    del books[book_id]

    remaining_books = len(books)
    debug_msg = f"After removing book [{book_title}] id: [{book_id}] there are {remaining_books} books in the system"
    books_logger.debug(f"{debug_msg} | request #{g.request_num}")

    return jsonify({"result": remaining_books}), 200


### 8. Get Logger Level
@app.route('/logs/level', methods=['GET'])
def get_log_level():
    logger_name = request.args.get('logger-name')

    if logger_name not in ['request-logger', 'books-logger']:
        return "Error: Invalid logger name provided", 400

    logger = logging.getLogger(logger_name)

    level_name = logging.getLevelName(logger.level)

    return level_name, 200

### 9. Set Logger Level
@app.route('/logs/level', methods=['PUT'])
def set_log_level():
    logger_name = request.args.get('logger-name')
    logger_level = request.args.get('logger-level')

    if logger_name not in ['request-logger', 'books-logger']:
        return "Error: Invalid logger name provided", 400

    if logger_level not in ['INFO', 'DEBUG', 'ERROR']:
        return f"Error: Invalid logger level [{logger_level}] provided", 400

    logger = logging.getLogger(logger_name)

    if logger_level == 'INFO':
        logger.setLevel(logging.INFO)
    elif logger_level == 'DEBUG':
        logger.setLevel(logging.DEBUG)
    elif logger_level == 'ERROR':
        logger.setLevel(logging.ERROR)

    return logger_level, 200

app.run(host='0.0.0.0', port=8574)
