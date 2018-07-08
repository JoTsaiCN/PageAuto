# -*- coding: utf-8 -*-
import time
import yaml
from datetime import datetime
from functools import wraps

from selenium.webdriver import Remote as WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common import exceptions


_IMG_PREFIX_FMT = '%Y%m%d%H%M%S%f'


class PageDecorator:
    """
    Decorators for methods of PageObject Class.
    """

    @staticmethod
    def require_driver(func):
        """
        Object to call function must have attribute with specify type: WebDriver and specific name: driver,
        otherwise an AttributeError will be thrown.
        """
        @wraps(func)
        def wrapper(obj, *args, **kwargs):
            if hasattr(obj, 'driver') and isinstance(obj.driver, WebDriver):
                return func(obj, *args, **kwargs)
            else:
                raise AttributeError('"{obj}" must have driver to call {f}'.format(obj=obj.name, f=func.__name__))
        return wrapper

    @staticmethod
    def switch_frame(func):
        """
        If an element has an attribute with specify type: PageObject and specific name: frame,
        call WebDriver.switch_to() to switch to specify frame.
        """
        @wraps(func)
        def wrapper(obj, *args, **kwargs):
            mark = False
            if hasattr(obj, 'frame') and isinstance(obj.frame, PageObject):
                if obj.frame.find() is not None:
                    print('Switch to frame({frame})'.format(frame=obj.frame.name))
                    obj.driver.switch_to.frame(obj.frame.eles[0])
                    mark = True
                else:
                    raise exceptions.NoSuchFrameException('Frame({frame}) is not found'.format(frame=obj.frame.name))
            ret = func(obj, *args, **kwargs)
            if mark:
                obj.driver.switch_to.default_content()
                print('Switch back to default content')
            return ret
        return wrapper

    @staticmethod
    def highlight(func):
        """
        Highlight the element during the function execution.
        """
        @wraps(func)
        def wrapper(obj, *args, **kwargs):
            origin_style = obj.ele.get_attribute("style")
            obj.driver.execute_script("arguments[0].style.border='2px solid red'", obj.ele)
            ret = func(obj, *args, **kwargs)
            try:
                obj.driver.execute_script("arguments[0].style.border='{0}'".format(origin_style), obj.ele)
            except exceptions.NoSuchElementException:
                pass
            return ret
        return wrapper

    @staticmethod
    def screenshot(func):
        """
        Take screenshot before and after the function execution.
        """
        @wraps(func)
        def wrapper(obj, *args, **kwargs):
            obj.driver.save_screenshot('{time}_{name}_before_{f}.png'.format(
                time=datetime.now().strftime(_IMG_PREFIX_FMT), name=obj.name, f=func.__name__))
            ret = func(obj, *args, **kwargs)
            obj.driver.save_screenshot('{time}_{name}_after_{f}.png'.format(
                time=datetime.now().strftime(_IMG_PREFIX_FMT), name=obj.name, f=func.__name__))
            return ret
        return wrapper


# For PageObject
_ELE_TREE = 'ele_tree'
BY_LIST = [value for key, value in By.__dict__.items() if key.find('__') == -1]
_INVALID_ELE_NAME = list(object.__dict__.keys()) + list(WebElement.__dict__.keys()) + [_ELE_TREE]


class PageObject(object):
    """
    Describe and operate a web page.

    :Attributes:
     - name -
     - pattern -
     - by -
     - timeout -
     - gap -
     - ignore -
     - is_frame -
     - order -
     - ele_tree -
     - pre_ele -
     - frame -
     - eles -
     - last_found -
    """

    DEFAULT_ATTRIBUTE = {
        'by': By.CSS_SELECTOR,
        'timeout': 5,
        'gap': 1,
        'ignore': (exceptions.NoSuchElementException,),
        'is_frame': False,
        'order': 0
    }

    def __init__(self, page_dict, pre_ele=None, frame=None):
        """
        Create a new page object to describe and operate a web page.

        :Args:
         - page_dict - A dictionary of description of a web page
         - pre_ele -
         - frame -
        """
        self.__dict__ = dict(self.__dict__, **PageObject.DEFAULT_ATTRIBUTE)
        for name, page in page_dict.items():
            if name in _INVALID_ELE_NAME:
                raise ValueError('Page\'s "name": "{0}" is invalid, cannot in {1}'.format(name, str(_INVALID_ELE_NAME)))
            if 'pattern' not in page:
                raise ValueError('Page({name}) must have attribute: "pattern"'.format(name=self.name))
            if 'by' in page and page['by'] not in BY_LIST:
                raise ValueError('Page({name})\'s "by": "{0}" is invalid, must in: {1}'.format(
                    page['by'], str(BY_LIST), name=self.name))

            self.name = name
            self.pre_ele = pre_ele
            self.frame = frame

            if _ELE_TREE in page:
                self.ele_tree = page[_ELE_TREE]
                page.pop(_ELE_TREE)
                # If current element is a frame, the frame of child element is current element,
                # otherwise the frame of child element is the incoming parameter: frame.
                ele_frame = self if page.get('is_frame', False) else self.frame
                for ele in self.ele_tree:
                    self.ele_tree[ele] = PageObject({ele: self.ele_tree[ele]}, pre_ele=self, frame=ele_frame)

            self.__dict__ = dict(self.__dict__, **page)
            self.last_found = 0
            self.eles = None
            break

    def __getattr__(self, item):
        try:
            return super().__getattribute__(item)
        except AttributeError as e:
            # Access child element as attribute, and call methods of WebElement as method.
            if item in WebElement.__dict__:
                return getattr(self.ele, item)
            elif _ELE_TREE in self.__dict__ and item in self.__dict__[_ELE_TREE]:
                return self.__dict__[_ELE_TREE][item]
            else:
                raise e

    def __repr__(self):
        return '<PageObject>{name: {self.name}, pattern: {self.pattern}, pre_ele: {pre}}'.format(
            self=self, pre=self.pre_ele.name if self.pre_ele else self.pre_ele)

    @property
    def ele(self):
        """
        Return element with specific order in the element list was found,
        otherwise return None.
        """
        if self.find(src='ele') is not None and self.order < self.count:
            return self.eles[self.order]
        else:
            return None

    @property
    def count(self):
        if self.eles is not None:
            return len(self.eles)
        else:
            return 0

    def set_driver(self, driver):
        self.driver = driver
        if hasattr(self, _ELE_TREE):
            for element in self.ele_tree.values():
                element.set_driver(driver)

    @PageDecorator.require_driver
    def find(self, src=''):
        """
        Finds elements.
        """
        if self.eles is not None and time.time() - self.last_found < self.gap:
            if src == 'ele':
                # Call from PageObject.ele
                return self.eles
            else:
                return self.ele
        # Clean found element list
        self.eles = None

        # If current element is the root element of the page, or the parent element is a frame,
        # call WebDriver.find_elements() to find elements,
        # otherwise call WebElement.find_elements().
        if self.pre_ele is None or self.pre_ele.is_frame:
            temp_pre_ele = self.driver
        else:
            # If call WebElement.find_elements(), find parent element first.
            if self.pre_ele.find() is None:
                raise exceptions.NoSuchElementException(
                    'Pre_ele of "{self.name}": "{self.pre_ele.name}" is not found'.format(self=self))
            else:
                temp_pre_ele = self.pre_ele.ele
        method = getattr(type(temp_pre_ele), 'find_elements')
        try:
            # Find elements and update the time of last found.
            self.eles = WebDriverWait(
                temp_pre_ele, self.timeout, self.gap, self.ignore
            ).until(
                lambda x: method(x, self.by, self.pattern)
            )
            self.last_found = time.time()
            print('Found element({self.name}<{self.by}("{self.pattern}")>)'.format(self=self))
            return self.eles
        except exceptions.TimeoutException:
            # Element is not found.
            print('Timeout to find element({self.name})<{self.by}("{self.pattern}")>'.format(
                self=self, pre=temp_pre_ele))

    @PageDecorator.require_driver
    @PageDecorator.switch_frame
    @PageDecorator.highlight
    @PageDecorator.screenshot
    def click(self):
        return self.ele.click()

    @PageDecorator.require_driver
    @PageDecorator.switch_frame
    @PageDecorator.highlight
    @PageDecorator.screenshot
    def send_keys(self, *value):
        return self.ele.send_keys(*value)


def get_page_with_yaml(path, driver=None):
    """
    Initial and return a PageObject with yaml file.

    Args:
     - path -
     - driver -
    """
    with open(path) as y:
        page_dict = yaml.load(y)
        page_object = PageObject(page_dict)
        if driver:
            page_object.set_driver(driver)
        return page_object


class PageTemplate(object):
    """
    A template for PageObject.

    :Args:
     - page_template - A string read from yaml file which describe a web page template.
    """

    def __init__(self, path):
        """
        Create a page template to describe a web page template.

        :Args:
         - path - A dictionary of description of a web page
        """
        with open(path) as y:
            self.page_template = y.read()

    def render(self, mapping, driver=None):
        """
        Return a page object with page template.

        :Args:
         - mapping - A dictionary.
         - driver -
        """
        page_yaml_str = self.page_template.format(**mapping)
        page_dict = yaml.load(page_yaml_str)
        page_object = PageObject(page_dict)
        if driver:
            page_object.set_driver(driver)
        return page_object
