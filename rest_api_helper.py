# MIT License

# Copyright (c) 2017 Ron Michael Khu, CodeRamen.Tech

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from flask import Flask, Response, request
import json, os, pprint, uuid, inspect, threading, atexit

from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper


class Util:

    @staticmethod
    def crossdomain(origin=None, methods=None, headers=None,
                    max_age=21600, attach_to_all=True,
                    automatic_options=True):
        """
        from: http://flask.pocoo.org/snippets/56/ 
        """
        if methods is not None:
            methods = ', '.join(sorted(x.upper() for x in methods))
        if headers is not None and not isinstance(headers, basestring):
            headers = ', '.join(x.upper() for x in headers)
        if not isinstance(origin, basestring):
            origin = ', '.join(origin)
        if isinstance(max_age, timedelta):
            max_age = max_age.total_seconds()

        def get_methods():
            if methods is not None:
                return methods

            options_resp = current_app.make_default_options_response()
            return options_resp.headers['allow']

        def decorator(f):
            def wrapped_function(*args, **kwargs):
                if automatic_options and request.method == 'OPTIONS':
                    resp = current_app.make_default_options_response()
                else:
                    resp = make_response(f(*args, **kwargs))
                if not attach_to_all and request.method != 'OPTIONS':
                    return resp

                h = resp.headers

                h['Access-Control-Allow-Origin'] = origin
                h['Access-Control-Allow-Methods'] = get_methods()
                h['Access-Control-Max-Age'] = str(max_age)
                if headers is not None:
                    h['Access-Control-Allow-Headers'] = headers
                return resp

            f.provide_automatic_options = False
            return update_wrapper(wrapped_function, f)
        return decorator

    """Contains assorted utility or helper methods for this module
    """

    @staticmethod
    def print_frame():
      """Print fields that would be helpful in debugging. It is an attempt to 
      create an equivalent for the printing __FILE__, __LINE__ and __FUNC__ 
      in C/C++. 
      
      """

      frame_record = inspect.stack()[1]         # 0 represents this line
                                                # 1 represents line at caller
      frame = frame_record[0]
      info = inspect.getframeinfo(frame)
      print info.filename, ':', info.lineno, '-', info.function 

class CollectionConfig:
    def __init__(self, name, id_field, data_file):
        """Defines a new collection config

        Args:
            name: collection name
            id_field: field in a single collection entry that would be 
                considered as the ID column or ID field that would be unique for 
                all the entries of the collection
            data_file: path to the data file that would store the collection 
                entries

        Returns:
            None
        """        

        self.name = name
        self.id_field = id_field
        self.data_file = data_file 

class DataHelper:

    @staticmethod
    def add_entry(records, collection, entry):

        logical_id_field = LazyManager.collection_configs[collection].id_field
        if not entry.has_key(logical_id_field):
            return 400, str('')

        id_value = entry[logical_id_field]

        if entry.has_key('__id__'):
            pass
        else:
            entry['__id__'] = str(uuid.uuid4())

        entries = records[collection]
        
        if entries.has_key(id_value):

            old_entry = entries[id_value]

            # Must validate against existing entry.
            # Check if the old and new entry has the same internal ID
            if not old_entry['__id__'] == entry['__id__']:
                return 400, '{"error": "non matching IDs"}'

        entries[id_value] = entry    

        return 200, json.dumps(entry)

    @staticmethod
    def load_data(path):
        """Loads the contents of the specified collection data file as JSON. If 
        the data file is not found, this method will attempt to create it.

        Args:
            path: data file path

        Returns:
            list of collection entries loaded
        """

        if not os.path.isfile(path):            # Create file if file not found

            # Create necessary parent directories
            basedir = os.path.dirname(path)
            if len(basedir) > 0 and not os.path.exists(basedir):
                os.makedirs(basedir)            # Create parent directories

            open(path, 'a').close()             # Create the file

        entries = []
        with open(path, 'r') as data_file:
            try:
                entries = json.load(data_file)
            except ValueError:
                entries = {}

        pprint.pprint(entries)
        return entries

    @staticmethod
    def save_data(path, data):
        """Saves specified collection as JSON contents in a data file.

        Args:
            path: data file path

        Returns:
            True on success; otherwise, false
        """

        if not os.path.isfile(path):            # Create file if file not found

            # Create necessary parent directories
            basedir = os.path.dirname(path)
            if len(basedir) > 0 and not os.path.exists(basedir):
                os.makedirs(basedir)            # Create parent directories

            open(path, 'a').close()             # Create the file

        with open(path, 'w') as data_file:
            try:
                entries = json.dump(data, data_file)
            except ValueError:
                return False

        return True

class LazyManager:
    """Serves as the manager or engine of this REST API service 

    Sample usage:
        <code>    
        configs = []
        configs.append(CollectionConfig('users', 'email', 'data_users.json'))

        manager = LazyManager()
        manager.init(configs)

        app = Flask(__name__)

        @app.route("/<collection>", defaults={'entry_id': None}, methods=['POST', 'GET'])
        @app.route("/<collection>/<entry_id>", methods=['PUT', 'GET'])
        def handle_volunteers(collection, entry_id):
            global manager
            return manager.process_request(request, collection, entry_id)

        if __name__ == "__main__":
            app.run(host='0.0.0.0')
        </code>
    """

    locks = {}
    records = {}
    collection_configs = {}

    def __init__(self):
        #self.data = []
        pass
    
    @staticmethod
    def init(collection_config_list):
        """Initializes the manager with a list of configuration for each 
        collection that it will manage.

        Args:
            collection_config_list: list of collection configuration

        Returns:
            None
        """

        for config in collection_config_list:
            LazyManager.collection_configs[config.name] = config
            LazyManager.locks[config.name] = threading.RLock()
            LazyManager.records[config.name] = DataHelper.load_data(config.data_file)

        atexit.register(LazyManager.handle_shutdown)

    def get_records(self):
        return LazyManager.records


    def get_data_entries(self, request, collection, entry_id):
        """Retrieves the entries associated with the specified collection.

        Args:
            request: Request object associated with the HTTP request
            collection: collection name
            entry_id: ID to find; needle in haystack

        Returns:
            HTTP response containing the list of entries as JSON content
        """

        collection = self.get_records()[collection]

        status = 200
        content = None

        if entry_id == None or len(entry_id) == 0:                
            content = json.dumps(collection)
        else:
            entry = next((i for k,i in collection.iteritems() 
                if i['__id__'] == entry_id), None)
            
            if entry == None:
                status = 404
            else:
                content = json.dumps(entry)

        #resp = content
        resp = Response(response=content,
                       status=status,
                       mimetype="application/json")

        return resp

    def delete_data_entry(self, request, collection, entry_id):
        """Deletes the data entry in the specified collection with
        the corresponding entry_id

        Args:
            request: Request object associated with the HTTP request
            collection: collection name
            entry_id: ID to find; needle in haystack

        Returns:
            HTTP response; 200 for success; otherwise, 404 
        """

        collection = self.get_records()[collection]

        status = 200
        content = None

        if entry_id == None or len(entry_id) == 0:                
            status = 404
        else:
            key = next((k for k,i in collection.iteritems() 
                if i['__id__'] == entry_id), None)
            
            if key == None:
                status = 404
            else:
                del collection[key]

        #resp = content
        resp = Response(response=content,
                       status=status,
                       mimetype="application/json")

        return resp

    def update_data_entry(self, request, collection, entry_id):
        """Updates the data entry in the specified collection with
        the corresponding entry_id

        Args:
            request: Request object associated with the HTTP request
            collection: collection name
            entry_id: ID to find; needle in haystack

        Returns:
            HTTP response; 200 for success; otherwise, 404 
        """

        entry = request.get_json(force=True, silent=True)
        if entry == None:
            return Response(status = 400)

        collection = self.get_records()[collection]

        status = 200

        if entry_id == None or len(entry_id) == 0:                
            status = 404
        else:
            key = next((k for k,i in collection.iteritems() 
                if i['__id__'] == entry_id), None)
            
            if key == None:
                status = 404
            else:
                pprint.pprint(entry)
                entry['__id__'] = collection[key]['__id__'] 
                collection[key] = entry

        #resp = content
        resp = Response(status=status)

        return resp

    def add_update_data_entries(self, request, collection):
        """Adds or updates entries in the collection associated with the 
        specified collection. 
        
        Entries will be extracted from the HTTP request body as JSON-encoded 
        content. The body is expected to contain a single dictionary or a list of
        dictionaries.
        
        Args:
            request: Request object associated with the HTTP request
            collection: collection name

        Returns:
            HTTP response containing the list of entries as JSON content
        """

        records = self.get_records()

        entry = request.get_json(force=True, silent=True)
        if entry == None:
            return Response(status = 400)

        if not isinstance(entry, list):
            status, content = DataHelper.add_entry(records, collection, entry)
        else:
            entries = entry
            contents = [] 

            for entry in entries:
                status, txt = DataHelper.add_entry(records, collection, entry)
                contents.append(txt)

            status = 200
            content = '[' + ','.join(contents) + ']'

        resp = Response(response=content,
                       status=status,
                       mimetype="application/json")

        return resp

    def process_request(self, request, collection, entry_id):
        """Process a REST operation on the specified collection. Operation
        will depend on the HTTP request method made. 
        
        Args:
            request: Request object associated with the HTTP request
            collection: collection name
            entry_id: ID (if any) of specific collection entry

        Returns:
            corresponding HTTP response
        """

        if not LazyManager.collection_configs.has_key(collection):
            return Response(status = 404)

        if request.method == 'GET' or request.method == 'OPTIONS' :
            return self.get_data_entries(request, collection, entry_id)

        if request.method == 'DELETE':
            return self.delete_data_entry(request, collection, entry_id)

        if request.method == 'PUT':
            if not entry_id == None:
                return self.update_data_entry(request, collection, entry_id)
            else:
                return self.add_update_data_entries(request, collection)

        elif request.method == 'POST':
            return self.add_update_data_entries(request, collection)


    @staticmethod
    def handle_url_single_filter(collection, req, resp, filter_list):
        config = LazyManager.collection_configs[collection]

        new_entries = {}                                   # new entries  
        for filter_key in filter_list:
            value = req.args.get(filter_key)    
            if not value:
                continue

            for txt in resp.response:                          # for all response texts 
                dictionary = json.loads(txt)                   # convert to dictionary of __id__->entry

                for k, entry in dictionary.iteritems():        # Traverse dictionary of entries
                    if entry[filter_key] == value:             # Filter
                        new_entries[entry[config.id_field]] = entry

            resp = Response(response=json.dumps(new_entries),
                           status=200,
                           mimetype="application/json")
        return resp


    @staticmethod
    def handle_shutdown():

        for name, config in LazyManager.collection_configs.iteritems():
             DataHelper.save_data(config.data_file, LazyManager.records[config.name])



