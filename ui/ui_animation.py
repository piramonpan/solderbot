from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QPoint, Qt
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QPushButton, QLabel

class UIAnimation():
    # Store animations here so they don't get deleted by Python
    _fade_in_anims = []
    _fade_out_anims = [] 

    @staticmethod
    def toggle_menu(app, sidebar):
        is_expanded = sidebar.width() < 100
        
        # --- Sidebar Width Animation ---
        app.animation = QPropertyAnimation(sidebar, b"minimumWidth")
        app.animation.setDuration(300)
        app.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        app.animation.valueChanged.connect(lambda v: sidebar.setMaximumWidth(v))
        
        start_val = sidebar.width()
        end_val = 150 if is_expanded else 60
        
        # UI Text Update
        if is_expanded:
            app.btn_editor.setText("📁 Project")
            app.btn_control.setText("⚙️ Control")
        else:
            app.btn_editor.setText("📁")
            app.btn_control.setText("⚙️")

        app.animation.setStartValue(start_val)
        app.animation.setEndValue(end_val)
        app.animation.start()

        # --- Fade Animation ---
        UIAnimation._fade_in_anims.clear() # Clear old references
        UIAnimation._fade_out_anims.clear() # Clear old references

        for button in sidebar.findChildren(QPushButton):
            button.show()
            UIAnimation.fade_in_widget(button, 1000)

    @staticmethod
    def fade_out_widget(widget, duration=500):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        # Keep reference alive in the class-level list
        UIAnimation._fade_out_anims.append(anim)
        anim.start()

    @staticmethod # Changed to static to match toggle_menu
    def fade_in_widget(widget, duration=500):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        # Keep reference alive in the class-level list
        UIAnimation._fade_in_anims.append(anim)
        anim.start()