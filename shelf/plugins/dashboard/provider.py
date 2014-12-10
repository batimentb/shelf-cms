class BaseProvider:
    def compute():
        raise NotImplementedError


class TextProvider(BaseProvider):
    def get_data(self):
        raise NotImplementedError

    def get_legend(self):
        raise NotImplementedError

    def compute(self):
        return {
            "data": self.get_data(),
            "legend": self.get_legend()
        }


class PictureTextProvider(TextProvider):
    def get_picture(self):
        raise NotImplementedError

    def compute(self):
        return {
            "data": self.get_data(),
            "legend": self.get_legend(),
            "picture": self.get_picture()
        }


class DonutProvider(BaseProvider):
    def get_legend(self):
        raise NotImplementedError

    def get_points(self):
        raise NotImplementedError

    def compute(self):
        return {
            "legend": self.get_legend(),
            "points": self.get_points()
        }


class EvolutionProvider(BaseProvider):
    def get_data(self):
        raise NotImplementedError

    def get_legend(self):
        raise NotImplementedError

    def get_points(self):
        raise NotImplementedError

    def compute(self):
        return {
            "data": self.get_data(),
            "legend": self.get_legend(),
            "points": self.get_points()
        }

class BarProvider(BaseProvider):
    def get_points(self):
        raise NotImplementedError

    def get_max(self):
        raise NotImplementedError

    def get_total(self):
        raise NotImplementedError

    def compute(self):
        return {
            "points": self.get_points(),
            "max": self.get_max(),
            "total": self.get_total()
        }

