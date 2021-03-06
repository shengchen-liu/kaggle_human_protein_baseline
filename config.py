class DefaultConfigs(object):
    # train_data = "../Human_Protein_Atlas/input/train/" # where is your train data
    # test_data = "../Human_Protein_Atlas/input/test/"   # your test data
    train_data = "./input/train/"  # where is your train data
    test_data = "./input/test/"  # your test data

    logs = "./results/logs/"
    weights = "./results/checkpoints/"
    best_models = "./results/checkpoints/best_models/"
    submit = "./results/submit/"
    model_name = "bninception_bcelog"
    num_classes = 28
    img_weight = 512
    img_height = 512
    channels = 4
    lr = 1e-4
    batch_size = 40
    epochs = 50
    resume = True
    initial_checkpoint = '0'
    gpus = "0,1,2,3"
    mode = 'train'
    threshold=0.3
    checkpoint = 0
    loss="bcelog"
    fold=0
    channels=3
    model='resnet34'

config = DefaultConfigs()