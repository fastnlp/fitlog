
from fitlog.fastserver.app import start_app

def run_app():

    log_dir ='/hdd/fudanNLP/fastNLP/tutorial/classification/with_fastnlp/logs'
    log_config_name = 'default-cfg.config'
    port = 5000
    start_app(log_dir, log_config_name, port, 1, '123')

if __name__ == '__main__':
    run_app()