"""Sucpicion detection class which performs various detections from frame."""
import numpy as np

from core.classifiers import EventDetector
from core.classifiers import Inception
from core.classifiers import UnusualActivityDetector
from core.classifiers import YOLOClassifier
from core.platform.async import async
import vgconf


class SuspicionDetection(object):
    async = async.Async()

    def __init__(self):
        self.yolo_inference_buffer = []
        self.inception_inference_buffer = []
        self.activity_detector_inference_buffer = []
        self.event_detector_inference_buffer = []
        self.yolo_buffer = []
        self.inception_buffer = []
        self.activity_detector_buffer = []
        self.event_detector_buffer = []

        self._yolo_buffer_lock = self.async.get_lock()
        self._inception_buffer_lock = self.async.get_lock()
        self._activity_detector_buffer_lock = self.async.get_lock()
        self._event_detector_buffer_lock = self.async.get_lock()

        self.is_inception_on = False
        self.inception = None

        self.is_event_detector_on = False
        self.event_detector = None

        self.is_activity_detector_on = False
        self.activity_detector = None
        self.activity_detector_length = vgconf.ACTIVITY_DETECTOR_LENGTH

        self.is_yolo_on = False
        self.yolo = None

        self.yolo_sample_rate = vgconf.DEFAULT_YOLO_SAMPLE_RATE
        self.inception_sample_rate = vgconf.DEFAULT_INCEPTION_SAMPLE_RATE

        self.count = 0
        self.sample_rate_lcm = self._get_sample_rate_lcm()

    def _get_gcd(self, a, b):
        while b > 0:
            a, b = b, a % b
        return a

    def _get_lcm(self, a, b):
        return (a * b) / self._get_gcd(a, b)

    def _get_sample_rate_lcm(self):
        return self._get_lcm(self.yolo_sample_rate, self.inception_sample_rate)

    def _get_random_input(self, shape):
        return np.random.uniform(size=shape)

    def _get_event_detector(self):
        self.event_detector = EventDetector.EventDetector()
        random_input = self._get_random_input((2048,))
        x = self.event_detector.predict(random_input)
        self.is_event_detector_on = True

    def _get_inception(self):
        self.inception = Inception.Inception()
        random_input = self._get_random_input((299, 299, 3))
        x = self.inception.predict(random_input)
        self.is_inception_on = True

    def _get_unusual_activity_detector(self):
        self.activity_detector = (
            UnusualActivityDetector.UnusualActivityDetector())
        random_input = self._get_random_input((4, 2048))
        x = self.activity_detector.predict(random_input)
        self.is_activity_detector_on = True

    def _get_yolo_classifier(self):
        self.yolo = YOLOClassifier.YOLO()
        random_input = self._get_random_input((299, 299, 3))
        x = self.yolo.predict(random_input)
        self.is_yolo_on = True

    def _remove_event_detector(self):
        # How to do this ???
        pass

    def _remove_inception(self):
        pass

    def _remove_unusual_activity_detector(self):
        pass

    def _remove_yolo_classifier(self):
        pass

    def enable_unusual_activity_detection(self):
        if not self.is_inception_on:
            self._get_inception()
        self._get_unusual_activity_detector()

    def enable_event_detection(self):
        if not self.is_inception_on:
            self._get_inception()
        self._get_event_detector()

    def enable_yolo_detection(self):
        self._get_yolo_classifier()

    def set_yolo_sample_rate(self, rate):
        self.yolo_sample_rate = rate
        self.sample_rate_lcm = self._get_sample_rate_lcm()

    def set_inception_sample_rate(self, rate):
        self.inception_sample_rate = rate
        self.sample_rate_lcm = self._get_sample_rate_lcm()

    @async.synchronize(lock='_inception_buffer_lock')
    def _inception_callback(self, result):
        self.inception_buffer.append(result)
        if len(self.inception_buffer) > self.activity_detector_length:
            self.inception_buffer.pop(0)
        if self.is_event_detector_on:
            self.perform_event_detector_inference(self.inception_buffer[-1])
        if self.is_activity_detector_on:
            if len(self.inception_buffer) >= self.activity_detector_length:
                self.perform_activity_detector_inference(
                    self.inception_buffer[-self.activity_detector_length:])

    @async.async_call(callback=_inception_callback)
    def _inception_inference(self):
        if not self.inception_inference_buffer:
            return
        return self.inception.predict(self.inception_inference_buffer.pop(0))

    def perform_inception_inference(self, frame):
        self.inception_inference_buffer.append(frame)
        if len(self.inception_inference_buffer) > 1:
            self.inception_inference_buffer.pop(0)
        return self._inception_inference()

    @async.synchronize(lock='_inception_buffer_lock')
    def get_inception_prediction(self):
        if not self.inception_buffer:
            return []
        return self.inception_buffer[-1]

    @async.synchronize(lock='_yolo_buffer_lock')
    def _yolo_callback(self, result):
        if not result:
            return
        self.yolo_buffer.append(result)
        if len(self.yolo_buffer) > 1:
            self.yolo_buffer.pop(0)

    @async.async_call(callback=_yolo_callback)
    def _yolo_inference(self):
        if not self.yolo_inference_buffer:
            return
        return self.yolo.predict(self.yolo_inference_buffer.pop(0))

    def perform_yolo_inference(self, frame):
        self.yolo_inference_buffer.append(frame)
        if len(self.yolo_inference_buffer) > 1:
            self.yolo_inference_buffer.pop(0)
        return self._yolo_inference()

    @async.synchronize(lock='_yolo_buffer_lock')
    def get_yolo_prediction(self):
        if not self.yolo_buffer:
            return []
        return self.yolo_buffer[-1]

    @async.synchronize(lock='_activity_detector_buffer_lock')
    def _activity_detector_callback(self, result):
        self.activity_detector_buffer.append(result)
        if len(self.activity_detector_buffer) > 1:
            self.activity_detector_buffer.pop(0)

    @async.async_call(callback=_activity_detector_callback)
    def _activity_detector_inference(self):
        if not self.activity_detector_inference_buffer:
            return
        return self.activity_detector.predict(
            self.activity_detector_inference_buffer.pop(0))

    def perform_activity_detector_inference(self, frames):
        self.activity_detector_inference_buffer.append(frames)
        if len(self.activity_detector_inference_buffer) > 1:
            self.activity_detector_inference_buffer.pop(0)
        return self._activity_detector_inference()

    @async.synchronize(lock='_activity_detector_buffer_lock')
    def get_activity_detector_prediction(self):
        if not self.activity_detector_buffer:
            return None
        return self.activity_detector_buffer[-1]

    @async.synchronize(lock='_event_detector_buffer_lock')
    def _event_detector_callback(self, result):
        self.event_detector_buffer.append(result)
        if len(self.event_detector_buffer) > 1:
            self.event_detector_buffer.pop(0)

    @async.async_call(callback=_event_detector_callback)
    def _event_detector_inference(self):
        if not self.event_detector_inference_buffer:
            return
        return self.event_detector.predict(
            self.event_detector_inference_buffer.pop(0))

    def perform_event_detector_inference(self, frame):
        self.event_detector_inference_buffer.append(frame)
        if len(self.event_detector_inference_buffer) > 1:
            self.event_detector_inference_buffer.pop(0)
        return self._event_detector_inference()

    @async.synchronize(lock='_event_detector_buffer_lock')
    def get_event_detector_prediction(self):
        if not self.event_detector_buffer:
            return []
        return self.event_detector_buffer[-1]

    def detect(self, frame):
        if self.is_yolo_on:
            if self.count % self.yolo_sample_rate == 0:
                self.perform_yolo_inference(frame)

        if self.is_event_detector_on or self.is_activity_detector_on:
            if self.count % self.inception_sample_rate == 0:
                self.perform_inception_inference(frame)

        self.count += 1
        if self.count == self.sample_rate_lcm:
            self.count = 0

    def close(self):
        self.async.close()
