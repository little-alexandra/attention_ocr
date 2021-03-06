from layers import model as _model
from layers.conv import Conv
from layers.attention import AttentionLayer
from utils.sequence import SequenceData
from utils import util, logger as log,label_utils
from tensorflow.python.keras.callbacks import TensorBoard,EarlyStopping,ModelCheckpoint
from main import conf
import logging
from keras import backend as K
from tensorflow.python.keras.models import load_model

logger = logging.getLogger("Train")

def train(args):
    # TF调试代码 for tf debugging：
    # from tensorflow.python import debug as tf_debug
    # from tensorflow.python.keras import backend as K
    # sess = K.get_session()
    # sess = tf_debug.LocalCLIDebugWrapperSession(sess)
    # K.set_session(sess)

    charset = label_utils.get_charset(conf.CHARSET)
    conf.CHARSET_SIZE = len(charset)
    model, _, _ = _model.model(conf, args)

    train_sequence = SequenceData(name="训练",
                                  label_file="data/train.txt",
                                  charset_file="data/charset.txt",
                                  conf=conf,
                                  args=args,
                                  batch_size=args.batch)
    valid_sequence = SequenceData(name="验证",
                                  label_file="data/validate.txt",
                                  charset_file="data/charset.txt",
                                  conf=conf,
                                  args=args,
                                  batch_size=args.validation_batch)

    timestamp = util.timestamp_s()
    tb_log_name = conf.DIR_TBOARD+"/"+timestamp
    checkpoint_path = conf.DIR_CHECKPOINT+"/checkpoint-{}.hdf5".format(timestamp)

    # 如果checkpoint文件存在，就加载之
    if args.retrain:
        logger.info("重新开始训练....")
    else:
        logger.info("基于之前的checkpoint训练...")
        _checkpoint_path = util.get_checkpoint(conf.DIR_CHECKPOINT)
        if _checkpoint_path is not None:
            model = load_model(_checkpoint_path,
                custom_objects={
                    'words_accuracy': _model.words_accuracy,
                    'Conv':Conv,
                    'AttentionLayer':AttentionLayer})
            logger.info("加载checkpoint模型[%s]", _checkpoint_path)
        else:
            logger.warning("找不到任何checkpoint，重新开始训练")

    checkpoint = ModelCheckpoint(
        filepath=checkpoint_path,
        monitor='words_accuracy',
        verbose=1,
        save_best_only=True,
        mode='max')

    early_stop = EarlyStopping(
        monitor='words_accuracy',
        patience=args.early_stop,
        verbose=1,
        mode='max')

    logger.info("Begin train开始训练：")

    # 训练STEPS_PER_EPOCH个batch，作为一个epoch，默认是10000
    model.fit_generator(
        generator=train_sequence,
        steps_per_epoch=args.steps_per_epoch,#其实应该是用len(train_sequence)，但是这样太慢了，所以，我规定用一个比较小的数，比如1000
        epochs=args.epochs,
        workers=args.workers,
        callbacks=[TensorBoard(log_dir=tb_log_name),checkpoint,early_stop],
        use_multiprocessing=False,
        validation_data=valid_sequence,
        validation_steps=args.validation_steps)

    logger.info("Train end训练结束!")

    model_path = conf.DIR_MODEL+"/ocr-attention-{}.hdf5".format(util.timestamp_s())
    model.save(model_path)
    logger.info("Save model保存训练后的模型到：%s", model_path)


if __name__ == "__main__":
    log.init()
    args = conf.init_args()
    with K.get_session(): # 防止bug：https://stackoverflow.com/questions/40560795/tensorflow-attributeerror-nonetype-object-has-no-attribute-tf-deletestatus
        train(args)