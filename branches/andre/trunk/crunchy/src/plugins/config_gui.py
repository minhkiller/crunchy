"""
config_gui.py : a plugin to enable users to configure crunchy nicely.

"""
from src.interface import plugin, config, SubElement
import src.configuration as configuration

def register():
    '''registers two http handlers: /config and /set_config and a begin page
    handler to insert the configuration page'''
    plugin['register_http_handler'](
                    "/set_config%s" % plugin['session_random_id'], set_config)
    plugin['register_tag_handler']("div", "title", "preferences", insert_preferences)

def insert_preferences(page, elem, uid):
    '''insert the requested preference choosers on a page'''
    if not page.includes("set_config"):
        page.add_include("set_config")
        page.add_js_code(set_config_jscode)
        page.add_css_code(config_gui_css)
    # The original div in the raw html page may contain some text
    # as a visual reminder that we need to remove here.
    elem.text = ''
    elem.attrib['class'] = 'config_gui'
    parent = SubElement(elem, 'dl')
    username = page.username
    to_show = elem.attrib['title'].split(' ')
    if len(to_show) == 1: # choices = "preferences"; all values are shown
        to_show = ['boolean', 'multiple_choice', 'user_defined']
    show(parent, username, uid, to_show)
    return

def set_config(request):
    """Http handler to set an option"""
    info = request.data.split("__SEPARATOR__")
    key = info[0]
    value = '__SEPARATOR__'.join(info[1:])
    option = ConfigOption.all_options[key]
    option.set(value)

def show(parent, username, uid, to_show=None):
    '''Shows all the requested configuration options in alphabetical order.'''
    if to_show is None:
        return
    keys = []
    for key in configuration.options:
        _type = select_option_type(key, username, uid)
        if (_type in to_show) or (key in to_show):
            keys.append(key)
    keys.sort()
    for key in keys:
        ConfigOption.all_options[key].render(parent)
    return

def select_option_type(key, username, uid, allowed_options=configuration.options,
                       ANY=configuration.ANY):
    '''select the option type to choose based on the key requested'''
    if key in config[username]:
        if set(allowed_options[key]) == set((True, False)):
            BoolOption(key, config[username][key], username, uid)
            _type = 'boolean'
        elif ANY in allowed_options[key]:
            StringOption(key, config[username][key], username, uid)
            _type = 'user_defined'
        elif key in allowed_options:
            MultiOption(key, config[username][key], allowed_options[key],
                        username, uid)
            _type = 'multiple_choice'
        else:
            print "Unexpected error in select_option_type; option = ", key
            print "not found in configuration.options but found in config[]."
    else:
        print key, "is not a valid configuration option"
        return False
    return _type

def get_prefs(username):
    """Return the preference object"""
    return config[username]['symbols'][config[username]['_prefix']]

class ConfigOption(object):     # tested
    """Generic option class"""
    all_options = {}

    def __init__(self, key, initial, username=None, uid=None):
        self.key = key
        self.uid = uid
        self.username = username
        self.set(initial)
        ConfigOption.all_options[key] = self

    def get(self):
        """Return the current value of the option"""
        return self.value

    def set(self, value):
        """sets and saves the value of the option"""
        self.value = value
        get_prefs(self.username)._save_settings(self.key, value)

class MultiOption(ConfigOption):
    """An option that has multiple predefined choices
    """
    # the threshold between radio buttons and a dropdown box
    threshold = 4

    def __init__(self, key, initial, values, username=None, uid=None):
        self.values = values
        super(MultiOption, self).__init__(key, initial, username=username, uid=uid)

    def get_values(self):
        """get the possible values"""
        return self.values

    def set(self, value):
        """Define the value of the option
        Convert str(None) in the python None object only if needed.
        """
        if None in self.get_values() and value == str(None):
            value = None
        super(MultiOption, self).set(value)

    def render(self, elem):
        """render the widget to a particular file object"""
        values = self.get_values()
        option = SubElement(elem, 'dt')
        # we use a unique id, rather than simply the key, in case two
        # identical preference objects are on the same page...
        _id = str(self.uid) + "__KEY__" + str(self.key)
        if len(values) <= MultiOption.threshold:
            option.text = "%s: " % self.key
            SubElement(option, 'br')
            for value in values:
                input = SubElement(option, 'input',
                    type = 'radio',
                    name = self.key,
                    id = "%s_%s" % (_id, str(value)),
                    onchange = "set_config('%(id)s_%(value)s', '%(key)s');" \
                        % {'id': _id, 'key': self.key, 'value': str(value)},
                )
                if value == self.get():
                    input.attrib['checked'] = 'checked'
                label = SubElement(option, 'label')
                label.attrib['for'] = "%s_%s" % (self.key, str(value))
                label.text = str(value)
                SubElement(option, 'br')
        else:
            label = SubElement(option, 'label')
            label.attrib['for'] = self.key
            label.text = "%s: " % self.key
            select = SubElement(option, 'select',
                name = self.key,
                id = _id,
                onchange = "set_config('%s', '%s');" % (_id, self.key)
            )
            for value in values:
                select_elem = SubElement(select, 'option', value = str(value))
                if value == self.get():
                    select_elem.attrib['selected'] = 'selected'
                select_elem.text = str(value) # str( ) is needed for None
        desc = SubElement(elem, 'dd')
        desc.text = str(getattr(get_prefs(self.username).__class__, self.key).__doc__)

class BoolOption(ConfigOption):
    """An option that has two choices [True, False]
    """
    def render(self, elem):
        """render the widget to a particular file object"""
        option = SubElement(elem, 'dt')
        _id = str(self.uid) + "__KEY__" + str(self.key)
        input = SubElement(option, 'input',
            type = 'checkbox',
            name = self.key,
            id = _id,
            onchange = "set_config('%s', '%s');" % (_id, self.key)
        )
        if self.get():
            input.attrib['checked'] = 'checked'
        label = SubElement(option, 'label')
        label.attrib['for'] = self.key
        label.text = self.key
        desc = SubElement(elem, 'dd')
        desc.text = str(getattr(get_prefs(self.username).__class__, self.key).__doc__)

    def set(self, value):
        """Define the value of the option
        This function replace the javascript "true" and "false value by python
        objects True and False.
        """
        if value not in [True, False]:
            if value.lower() == "true":
                value = True
            else:
                value = False
        super(BoolOption, self).set(value)

class StringOption(ConfigOption):
    """An option that can have any value
    """
    def render(self, elem):
        """render the widget to a particular file object"""
        option = SubElement(elem, 'dt')
        label = SubElement(option, 'label')
        label.attrib['for'] = self.key
        label.text = "%s: " % self.key
        _id = str(self.uid) + "__KEY__" + str(self.key)
        input = SubElement(option, 'input',
            type = 'text',
            id = _id,
            name = self.key,
            value = self.get(),
            onchange = "set_config('%s', '%s');" % (_id, self.key)
        )
        desc = SubElement(elem, 'dd')
        desc.text = str(getattr(get_prefs(self.username).__class__, self.key).__doc__)

set_config_jscode = """
function set_config(id, key){
    var value;
    field=document.getElementById(id)
    // find the value depending of the type of input
    if (field.type == 'checkbox') {
        value = field.checked;
    }
    else if ((field.type != 'radio') || (field.checked)) {
        // exclude unchecked radio
        value = field.value;
    }

    // if needed, send the new value
    if (value != undefined) {
        var j = new XMLHttpRequest();
        j.open("POST", "/set_config%s", false);
        j.send(key+"__SEPARATOR__"+value);
    }
};
""" % plugin['session_random_id']

config_gui_css = """
.config_gui dt{
    position:relative;
    width:50%;
    top: 1em;
}
.config_gui dd{
    position:relative;
    padding-left:50%;
    text-align:left;
    border-bottom: 1px dotted black;
    width:50%;
}"""
