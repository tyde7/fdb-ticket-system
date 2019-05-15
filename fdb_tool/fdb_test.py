import itertools
import traceback

import fdb, time
import fdb.tuple

fdb.api_version(600)

####################################
##        Initialization          ##
####################################

# Data model:
# ('attends', student, class) = ''
# ('class', class_name) = seats_left

db = fdb.open()
scheduling = fdb.directory.create_or_open(db, ('scheduling',))
course = scheduling['concerts']
attends = scheduling['attends']


@fdb.transactional
def add_class(tr, c):
    tr[course.pack(c)] = fdb.tuple.pack((100,))

def exeTime(func):
    def newFunc(*args, **args2):
        t0 = time.time()
        print("@%s, {%s} start" % (time.strftime("%X", time.localtime()), func.__name__))
        back = func(*args, **args2)
        print("@%s, {%s} end" % (time.strftime("%X", time.localtime()), func.__name__))
        print("@%.3fs taken for {%s}" % (time.time() - t0, func.__name__))
        return back
    return newFunc


# Generate 1,620620 classes like '9:00 chem for dummies'
# Generate 792 names like '9:00 chem for dummies'
levels = ['张惠妹', '林俊杰', '周杰伦', '五月天', '杨坤', '王力宏',
          'A-Lin', '苏打绿', '陈奕迅', '张惠妹', '孙燕姿']
types = ['上海', '南京', '北京', '武汉', '杭州', '郑州',
         '西安', '深圳', '重庆', '成都', '广州', '福州',
         '厦门', '长沙', '大连', '青岛', '常州', '合肥']
from random import sample

times = ['%d月' % h for h in range(1, 13)]
class_combos = itertools.product(levels, types, sorted(sample(times, 4)))
# class_names = [''.join(tup) + '演唱会' for tup in class_combos]
class_names = [tup for tup in class_combos]


@fdb.transactional
def init(tr):
    del tr[scheduling.range(())]  # Clear the directory
    for class_name in class_names:
        add_class(tr, class_name)


####################################
##  Class Scheduling Functions    ##
####################################


@fdb.transactional
def available_classes(tr):
    return [course.unpack(k)[0] for k, v in tr[course.range(())]
            if fdb.tuple.unpack(v)[0]]


@fdb.transactional
def signup(tr, s, c):
    rec = attends.pack((s, c))
    if tr[rec].present(): return  # already signed up

    seats_left = fdb.tuple.unpack(tr[course.pack(c)])[0]
    if not seats_left: raise Exception('No remaining seats')

    classes = tr[attends.range((s,))]
    if len(list(classes)) == 5: raise Exception('Bought too many tickets one time.')

    tr[course.pack(c)] = fdb.tuple.pack((seats_left - 1,))
    tr[rec] = b''


@fdb.transactional
def get_keys(tr, s):
    pairs = tr[attends.range((s,))]
    return [attends.unpack(k)[-1] for k, v in pairs]


@fdb.transactional
def get_all_attends(tr,conditions=()):
    pairs = tr[attends.range(conditions)]
    return [attends.unpack(k) for k, v in pairs]


@fdb.transactional
def get_all_concerts(tr, conditions=()):
    pairs = tr[course.range(conditions)]
    return [(course.unpack(k), fdb.tuple.unpack(v)[0]) for k, v in pairs]


@fdb.transactional
def drop(tr, s, c):
    rec = attends.pack((s, c))
    if not tr[rec].present(): return  # not taking this class
    tr[course.pack(c)]= fdb.tuple.pack((fdb.tuple.unpack(tr[course.pack(c)])[0] + 1,))
    del tr[rec]


@fdb.transactional
def switch(tr, s, old_c, new_c):
    drop(tr, s, old_c)
    signup(tr, s, new_c)


####################################
##           Testing              ##
####################################

import random
import threading


def indecisive_student(i, ops):
    student_ID = 's{:d}'.format(i)
    all_classes = class_names
    my_classes = []

    for i in range(ops):
        class_count = len(my_classes)
        moods = []
        if class_count: moods.extend(['drop', 'switch'])
        if class_count < 5: moods.append('add')
        mood = random.choice(moods)

        try:
            if not all_classes:
                all_classes = available_classes(db)
            if mood == 'add':
                c = random.choice(all_classes)
                signup(db, student_ID, c)
                my_classes.append(c)
            elif mood == 'drop':
                c = random.choice(my_classes)
                drop(db, student_ID, c)
                my_classes.remove(c)
            elif mood == 'switch':
                old_c = random.choice(my_classes)
                new_c = random.choice(all_classes)
                switch(db, student_ID, old_c, new_c)
                my_classes.remove(old_c)
                my_classes.append(new_c)
        except Exception as e:
            traceback.print_exc()
            print("Need to recheck available classes.")
            all_classes = []


def run(students, ops_per_student):
    threads = [
        threading.Thread(target=indecisive_student, args=(i, ops_per_student))
        for i in range(students)]
    for thr in threads: thr.start()
    for thr in threads: thr.join()
    print("Ran {} transactions".format(students * ops_per_student))

@fdb.transactional

def test_write(tr,times=10000):
    test = fdb.directory.create_or_open(tr, ('test',))
    test1 = test['data']
    del tr[test.range(())]  # Clear the directory
    from random import choice, randint
    for i in range(times):
        tr[course.pack(choice(class_names)+(randint(1,1000),))] = fdb.tuple.pack((100,))


@fdb.transactional
def test_read(tr,times=10000):
    test = fdb.directory.create_or_open(tr, ('test',))
    test1 = test['data']
    from random import choice
    for i in range(times):
        pairs = tr[test1.range(choice(class_names)[:-1])]
        _ = [test1.unpack(k) for k, v in pairs]


if __name__ == "__main__":
    init(db)
    print("initialized")
    run(10, 100)

def test():
    t0 = time.time()
    print("@%s, {%s} write start" % (time.strftime("%X", time.localtime()), test_write.__name__))
    test_write(db)
    print("@%s, {%s} end" % (time.strftime("%X", time.localtime()), test_write.__name__))
    print("@%.3fs taken for {%s}" % (time.time() - t0, test_write.__name__))
    t0 = time.time()
    print("@%s, {%s} write start" % (time.strftime("%X", time.localtime()), test_read.__name__))
    test_read(db)
    print("@%s, {%s} end" % (time.strftime("%X", time.localtime()), test_read.__name__))
    print("@%.3fs taken for {%s}" % (time.time() - t0, test_read.__name__))
