# coding=utf-8
"""Defines the DenseNet class"""
import torch
import torch.nn as nn

from .basenetwork import BaseNetwork
from .layers import DenseUnit

import logging
from inspect import getfullargspec

logger = logging.getLogger(__name__)


class DenseNetConfig:
    """
    Defines the necessary configuration for a DenseNet.
    """
    def __init__(self, raw_config):
        if 'dense_units' not in raw_config:
            raise KeyError("dense_units must be specified.")

        if not isinstance(raw_config['dense_units'], list):
            raise ValueError("dense_units must be of type list.")

        dense_unit_arg_spec = getfullargspec(DenseUnit)
        dense_unit_arg_spec.args.remove('self')

        # Find the index for where the defaulted values begin
        default_arg_start_index = len(dense_unit_arg_spec.args) - len(dense_unit_arg_spec.defaults)
        default_args = dense_unit_arg_spec.args[default_arg_start_index:]

        # Only look at args that were specified to be overwritten
        override_args = set(default_args).intersection(set(raw_config.keys()))
        # If arguments are specified in lists,
        # check that length corresponds to dense_units
        for arg in override_args:
            if isinstance(raw_config[arg], list):
                if len(raw_config[arg]) != len(raw_config['dense_units']):
                    raise ValueError("{} list must be same length as dense_units.".format(arg))
            else:
                # If a single value is specified, it will be applied to all layers
                raw_config[arg] = [raw_config[arg]] * len(raw_config['dense_units'])
        
        # TODO: Think about moving dimension to config file
        _units_per_layer = list([None] + raw_config['dense_units'])
        _unit_pairs = list(zip(_units_per_layer[:-1], _units_per_layer[1:]))

        self.units = []
        for i, (in_feature, out_feature) in enumerate(_unit_pairs):
            temp_unit = {
                'in_features': in_feature,
                'out_features': out_feature
            }
            for arg in override_args:
                temp_unit[arg] = raw_config[arg][i]
            self.units.append(temp_unit)


class DenseNet(BaseNetwork, nn.Module):
    """
    Subclass of BaseNetwork defining a DenseNet

    """

    def __init__(self, name, dimensions, config, save_path=None, input_networks=None, num_classes=None,
                 activation=nn.ReLU(), pred_activation=nn.Softmax(dim=1), optim_spec={'name': 'Adam', 'lr': 0.001},
                 lr_scheduler=None, early_stopping=None, criter_spec=nn.CrossEntropyLoss()):
        
        nn.Module.__init__(self)
        super(DenseNet, self).__init__(name, dimensions, DenseNetConfig(config), save_path, input_networks, num_classes,
                                       activation, pred_activation, optim_spec, lr_scheduler, early_stopping, criter_spec
                                       )

    def _create_network(self, **kwargs):

        dense_hid_layers = self._config.units
        # Build network
        self.network = self._build_dense_network(
            dense_hid_layers, kwargs['activation'])

        if self._num_classes:
            self.out_dim = self._num_classes
            self._create_classification_layer(
                dense_hid_layers[-1]['out_features'],
                kwargs['pred_activation'])

    def _create_classification_layer(self, dim, pred_activation):
        self.network_tail = DenseUnit(
            dim, self.out_dim, activation=pred_activation)

    def _forward(self, xs, **kwargs):
        """
        Computation for the forward pass of the DenseNet module.
        :param xs: input list(torch.Tensor)
        :return: output torch.Tensor
        """
        out = []
        for x in xs:
            if len(x.size())>2:
                x = x.view(x.size()[0], -1)
            out.append(x)

        network_output = self.network(torch.cat(out, dim=1))
        return network_output

    def _build_dense_network(self, dense_hid_layers, activation):
        """
        Utility function to build the layers into a nn.Sequential object.
        :param dims: The dimensions
        :return: the dense network as a nn.Sequential object
        """
        # Specify incoming feature size for the first dense hidden layer        
        dense_hid_layers[0]['in_features'] = sum(self.in_dim)
        dense_layers = []
        for dense_layer_config in dense_hid_layers:
            dense_layer_config['activation'] = activation
            dense_layers.append(DenseUnit(**dense_layer_config))
        dense_network = nn.Sequential(*dense_layers)
        return dense_network

    def __str__(self):
        if self.optim is not None:
            return super(DenseNet, self).__str__() + f'\noptim: {self.optim}'
        else:
            return super(DenseNet, self).__str__()
