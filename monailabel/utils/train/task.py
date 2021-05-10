import datetime
import logging
import time
from abc import abstractmethod

import torch
from monai.engines import SupervisedEvaluator, SupervisedTrainer

logger = logging.getLogger(__name__)


# TODO:: Think of some better abstraction/generalization here... few abstracts can be removed
#  And support Multi GPU
class TrainTask:
    @abstractmethod
    def device(self):
        """
        Provide device name
        """
        pass

    @abstractmethod
    def network(self):
        """
        Provide network
        """
        pass

    @abstractmethod
    def loss_function(self):
        """
        Provide Lost function
        """
        pass

    @abstractmethod
    def optimizer(self):
        """
        Provide Optimizer
        """
        pass

    @abstractmethod
    def train_pre_transforms(self):
        """
        Provide List of Pre-Transforms for training
        """
        pass

    @abstractmethod
    def train_post_transforms(self):
        """
        Provide List of Post-Transforms for training
        """
        pass

    @abstractmethod
    def train_data_loader(self):
        """
        Provide Dataloader for training samples
        """
        pass

    @abstractmethod
    def train_inferer(self):
        """
        Provide Inferer to be used while training
        """
        pass

    @abstractmethod
    def train_key_metric(self):
        """
        Provide List of Key Metrics to be collected while training
        """
        pass

    @abstractmethod
    def train_handlers(self):
        """
        Provide List of training handlers
        """
        pass

    @abstractmethod
    def train_additional_metrics(self):
        """
        Provide any additional metrics to be collected while training
        """
        return None

    @abstractmethod
    def val_pre_transforms(self):
        """
        Provide List of Pre-Transforms for validation step
        """
        pass

    @abstractmethod
    def val_post_transforms(self):
        """
        Provide List of Post-Transforms for validation step
        """
        pass

    @abstractmethod
    def val_inferer(self):
        """
        Provide Inferer to be used for validation step
        """
        pass

    @abstractmethod
    def val_data_loader(self):
        """
        Provide Dataloader for validation samples
        """
        pass

    @abstractmethod
    def val_handlers(self):
        """
        Provide List of handlers for validation
        """
        pass

    @abstractmethod
    def val_key_metric(self):
        """
        Provide List of Key metrics to be collected during validation
        """
        pass

    @abstractmethod
    def val_additional_metrics(self):
        """
        Provide any additional metrics to be collected while validation
        """
        return None

    def evaluator(self):
        self._evalutor = (
            SupervisedEvaluator(
                device=self.device(),
                val_data_loader=self.val_data_loader(),
                network=self.network().to(self.device()),
                inferer=self.val_inferer(),
                post_transform=self.val_post_transforms(),
                key_val_metric=self.val_key_metric(),
                additional_metrics=self.val_additional_metrics(),
                val_handlers=self.val_handlers(),
            )
            if self.val_data_loader()
            else None
        )
        return self._evalutor

    def __call__(self, max_epochs, amp):
        trainer = SupervisedTrainer(
            device=self.device(),
            max_epochs=max_epochs,
            train_data_loader=self.train_data_loader(),
            network=self.network().to(self.device()),
            optimizer=self.optimizer(),
            loss_function=self.loss_function(),
            inferer=self.train_inferer(),
            amp=amp,
            post_transform=self.train_post_transforms(),
            key_train_metric=self.train_key_metric(),
            train_handlers=self.train_handlers(),
        )

        logger.info(f"Running Training.  Epochs: {max_epochs}; AMP: {amp}")
        start = time.time()
        trainer.run()
        lapsed = str(datetime.timedelta(seconds=int(time.time() - start)))
        logger.info(f"++ Total Train Time:: {lapsed}")

        def tensor_to_list(d):
            for k, v in d.items():
                d[k] = v.tolist() if torch.is_tensor(v) else v

        stats = trainer.get_train_stats()
        stats["total_time"] = lapsed
        stats["train_metrics"] = trainer.state.metrics
        stats["train_metric_details"] = trainer.state.metric_details
        stats["train_key_metric_name"] = trainer.state.key_metric_name
        stats["train_best_metric"] = trainer.state.best_metric_epoch
        stats["train_best_metric_epoch"] = trainer.state.best_metric_epoch
        tensor_to_list(stats["train_metrics"])
        tensor_to_list(stats["train_metric_details"])

        if self._evalutor:
            stats["val_metrics"] = self._evalutor.state.metrics
            stats["val_metric_details"] = self._evalutor.state.metric_details
            stats["val_key_metric_name"] = self._evalutor.state.key_metric_name
            stats["val_best_metric"] = self._evalutor.state.best_metric_epoch
            stats["val_best_metric_epoch"] = self._evalutor.state.best_metric_epoch
            tensor_to_list(stats["val_metrics"])
            tensor_to_list(stats["val_metric_details"])

        logger.info(f"Train Task Stats: {stats}")
        return stats
