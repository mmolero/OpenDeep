"""
Please refer to the following tutorial in the documentation at www.opendeep.org

Tutorial: Your Second Model (Combining Layers)
"""
# standard libraries
import logging
# third party libraries
from opendeep.log.logger import config_root_logger
from opendeep.models.container import Prototype
from opendeep.models.single_layer.basic import BasicLayer, SoftmaxLayer
from opendeep.optimization.adadelta import AdaDelta
from opendeep.data.standard_datasets.image.mnist import MNIST
from opendeep.data.dataset import TEST

# grab a log to output useful info
log = logging.getLogger(__name__)

def create_mlp():
    # define the model layers
    relu_layer1 = BasicLayer(input_size=784, output_size=1000, activation='rectifier')
    relu_layer2 = BasicLayer(inputs_hook=(1000, relu_layer1.get_outputs()), output_size=1000, activation='rectifier')
    class_layer3 = SoftmaxLayer(inputs_hook=(1000, relu_layer2.get_outputs()), output_size=10, out_as_probs=False)
    # add the layers as a Prototype
    mlp = Prototype(layers=[relu_layer1, relu_layer2, class_layer3])

    mnist = MNIST()

    optimizer = AdaDelta(model=mlp, dataset=mnist, n_epoch=20)
    optimizer.train()

    test_data = mnist.getDataByIndices(indices=range(25), subset=TEST)
    # use the predict function!
    preds = mlp.predict(test_data)
    log.info('-------')
    log.info(str(preds))
    log.info(str(mnist.getLabelsByIndices(indices=range(25), subset=TEST)))

if __name__ == '__main__':
    config_root_logger()
    create_mlp()