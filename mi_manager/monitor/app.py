# -*- coding: utf-8 -*-
import redis
import json
import os
import dat_service
import settings
import url_extract_tools
import base64

from flask import Flask, render_template, jsonify, request, current_app, redirect, send_from_directory, abort
from gen_spiderInitfile_of_news import generate_spider_init

app = Flask(__name__)
app.config['BASEDIR'] = os.path.abspath(os.path.dirname(__file__)) # app.py所在的目录
app.config['UPLOAD_FOLDER'] = 'upload' # 用文件夹‘upload’来存储新上传的文件


# 用于判断文件后缀
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1] in ['txt','png','PNG','jpg','JPG','gif','GIF','xls','xlsx']

# 用于测试上传，稍后用到
@app.route('/test/upload')
def upload_test():
    return render_template('upload.html')

# 上传文件
@app.route('/api/upload',methods=['POST'],strict_slashes=False)
def api_upload():
    file_dir=os.path.join(app.config['BASEDIR'], app.config['UPLOAD_FOLDER'])
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    f=request.files['myfile']  # 从表单的file字段获取文件，myfile为该表单的name值
    if f and allowed_file(f.filename):  # 判断是否是允许上传的文件类型
        f.save(os.path.join(file_dir,f.filename))  #保存文件到upload目录
        token = base64.b64encode(f.filename)
        print token
        return jsonify({"msg":"upload success","token":token})
    else:
        return jsonify({"errno":1001,"errmsg":"upload fail"})

@app.route('/api/download',methods=['GET'],strict_slashes=False)
def download():
    filename = request.args.get('filename')
    if filename is None:
        filename = 'swap.txt'
    if request.method=="GET":
        if os.path.isfile(os.path.join('upload', filename)):
            return send_from_directory('upload',filename,as_attachment=True)
        abort(404)

@app.route('/')
def index():
    return redirect('/static/v2/login.html')


@app.route('/monitor')
def monitor():
    return render_template('index.html',
                           timeinterval=settings.TIMEINTERVAL,
                           stats_keys=settings.STATS_KEYS,
                           spider_name=request.args.get('spider_name'))


@app.route('/ajax')
def ajax():
    key = request.args.get('key')
    result = current_app.r.lrange(key, -settings.POINTLENGTH, -1)[::settings.POINTINTERVAL]
    if not current_app.spider_is_run:
        # spider is closed
        return json.dumps(result).replace('"', ''), 404
    return json.dumps(result).replace('"', '')


@app.route('/signal')
def signal():
    signal = request.args.get('sign')
    if signal == 'closed':
        current_app.spider_is_run = False
    elif signal == 'running':
        current_app.spider_is_run = True
    return jsonify('')


@app.route('/gen_spider', methods=['GET', 'POST'])
def gen_spider():
    jsonstr = request.form.get('json_result', '')
    js = dict(json.loads(jsonstr))
    start_urls = list(js['start_urls'])
    spider_name = url_extract_tools.extract_main_url(start_urls)
    dat_service.save_data(spider_name, jsonstr)
    generate_spider_init(jsonstr)
    return jsonify('ok')


@app.route('/add_ips', methods=['GET', 'POST'])
def add_ips():
    jsonstr = request.form.get('ips', '')
    ips_array = json.loads(jsonstr)['ips']
    dat_service.save_proxys(ips_array)
    return jsonify('ok')


@app.route('/target_urls', methods=['GET', 'POST'])
def target_urls():
    jsonstr = request.form.get('urls', '')
    urls_array = json.loads(jsonstr)['urls']
    dat_service.split_target_urls(urls_array)
    return jsonify('ok')

@app.route('/get_spider_names', methods=['GET'])
def get_spider_names():
    return jsonify(dat_service.get_spider_count_from_db())

@app.route('/start_work', methods=['GET'])
def get_start_work():
    # 初始化监控器数据
    dat_service.init_monitor()
    # 初始化mysql数据库
    dat_service.init_mysql()
    #
    dat_service.exec_init_of_missions()
    #
    return jsonify('ok')


# 慎用
@app.route('/init_monitor', methods=['GET'])
def init_monitor():
    return jsonify(dat_service.init_monitor())

# 在个API暂时没有实际意义
@app.route('/init_mysql', methods=['GET'])
def init_mysql():
    return jsonify(dat_service.init_mysql())

@app.route('/get_table', methods=['GET'])
def get_table():
    table_name = request.args.get('table_name')
    if table_name is None:
        data_dic = []
    if(table_name == 'Article'):
        data_dic = dat_service.get_data_from_mongo(table_name)
    elif(table_name == 'ECommerce' or table_name == 'ECommerceShop' or table_name == 'ECommerceShopComment' or table_name == 'ECommerceGood' or table_name == 'ECommerceGoodComment'):
        data_dic = dat_service.get_data_from_mysql(table_name)
    return jsonify(data_dic)



# 获取新闻爬虫名
@app.route('/get_news_spider_name', methods=['GET'])
def get_news_spider_name():
    r = redis.Redis(settings.REDIS_HOST, settings.REDIS_PORT, db=settings.SPIDERS_DB)
    keys = r.keys()
    return jsonify(keys)


# 获取爬虫配置
@app.route('/get_spider_info', methods=['GET'])
def get_spider_info():
    key = request.args.get('key')
    r = redis.Redis(settings.REDIS_HOST, settings.REDIS_PORT, db=settings.SPIDERS_DB)
    res = r.get(key)
    dic = eval(res)
    ss = json.dumps(dic)
    return ss


# 删除爬虫，形式：/delte_spider?key=163.com
@app.route('/delte_spider', methods=['GET'])
def delte_spider():

    # todo
    print '已删除..'
    return jsonify('ok')


# 删除全部爬虫
@app.route('/delte_all_spider', methods=['GET'])
def delte_all_spider():
    # todo
    print '已删除..'
    return jsonify('ok')


# 批量导入，注意是POST，文本参数在变量txt里
@app.route('/batch_import_spider', methods=['POST'])
def batch_import_spider():
    txt = request.form.get('txt', '')
    try:
        dat_service.batch_import_spider(txt)
        print '已批量导入..'
        return jsonify('ok')
    except:
        print '导入失败'

# 批量导出，直接返回文本就好
@app.route('/batch_export_spider', methods=['GET'])
def batch_export_spider():
    # todo
    ans = dat_service.batch_export_spider()

    return ans


@app.before_first_request
def init():
    current_app.r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.MONITOR_DB)
    if current_app.r.get('spider_is_run') == '1':
        current_app.spider_is_run = True
    else:
        current_app.spider_is_run = False


if __name__ == '__main__':
    # 产生包含ip和port的js文件
    text = 'POST_URL_PREFIX = "http://' + settings.APP_HOST + ':' + str(settings.APP_PORT) + '"'
    filename = os.getcwd() + settings.TEMP_PATH + '/static/const.js'
    with open(filename, 'w') as f:
        f.write(text.encode('utf8'))
    app.run(host=settings.APP_HOST, port=settings.APP_PORT, debug=False)
