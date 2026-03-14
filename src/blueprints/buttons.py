from flask import Blueprint, request, jsonify, current_app, render_template
import logging

logger = logging.getLogger(__name__)
buttons_bp = Blueprint("buttons", __name__)

@buttons_bp.route('/buttons')
def buttons_page():
    """Display the button configuration page."""
    device_config = current_app.config['DEVICE_CONFIG']
    
    # Get current button configuration
    button_config = device_config.get_config("button_config", {})
    
    # Get available plugins for dropdown
    available_plugins = device_config.get_plugins()
    
    # Define available buttons (could be made configurable later)
    available_buttons = ["SW_A", "SW_B", "SW_C", "SW_D"]
    
    return render_template('buttons.html', 
                         button_config=button_config,
                         available_plugins=available_plugins,
                         available_buttons=available_buttons)

@buttons_bp.route('/buttons/save', methods=['POST'])
def save_button_config():
    """Save button configuration."""
    try:
        device_config = current_app.config['DEVICE_CONFIG']
        
        # Parse form data
        button_config = {}
        available_buttons = ["SW_A", "SW_B", "SW_C", "SW_D"]
        
        for button in available_buttons:
            action_type = request.form.get(f"{button}_action_type")
            plugin_id = request.form.get(f"{button}_plugin_id")
            
            if action_type and plugin_id:
                # Validate plugin exists
                plugin_config = device_config.get_plugin(plugin_id)
                if not plugin_config:
                    return jsonify({"error": f"Plugin '{plugin_id}' not found for button {button}"}), 400
                
                button_config[button] = {
                    "action_type": action_type,
                    "plugin_id": plugin_id,
                    "plugin_settings": {}
                }
                
                # Dynamically handle plugin-specific settings based on form data
                # This follows the plugin documentation pattern where settings come from form inputs
                for key, value in request.form.items():
                    if key.startswith(f"{button}_plugin_") and not key.endswith("_plugin_id"):
                        # Extract the setting name (remove button prefix and plugin prefix)
                        setting_name = key.replace(f"{button}_plugin_", "")
                        if value:  # Only add non-empty values
                            button_config[button]["plugin_settings"][setting_name] = value
        
        # Update configuration
        device_config.update_value("button_config", button_config, write=True)
        
        logger.info(f"Button configuration updated: {button_config}")
        return jsonify({"success": True, "message": "Button configuration saved successfully"})
        
    except Exception as e:
        logger.error(f"Error saving button configuration: {e}")
        return jsonify({"error": f"Failed to save configuration: {str(e)}"}), 500

@buttons_bp.route('/buttons/plugin_settings/<plugin_id>')
def get_plugin_settings_template(plugin_id):
    """Get plugin-specific settings template for button configuration."""
    try:
        device_config = current_app.config['DEVICE_CONFIG']
        
        # Validate plugin exists
        plugin_config = device_config.get_plugin(plugin_id)
        if not plugin_config:
            return jsonify({"error": f"Plugin '{plugin_id}' not found"}), 404
        
        # Get plugin instance to access its settings template
        from plugins.plugin_registry import get_plugin_instance
        plugin = get_plugin_instance(plugin_config)
        
        # Get template parameters following the plugin documentation pattern
        template_params = plugin.generate_settings_template()
        
        # Return the settings template info that can be used to build dynamic forms
        return jsonify({
            "success": True,
            "plugin_id": plugin_id,
            "template_params": template_params
        })
        
    except Exception as e:
        logger.error(f"Error getting plugin settings template for {plugin_id}: {e}")
        return jsonify({"error": f"Failed to get plugin settings: {str(e)}"}), 500

@buttons_bp.route('/buttons/plugin_settings_html/<plugin_id>/<button_name>')
def get_plugin_settings_html(plugin_id, button_name):
    """Get rendered plugin settings HTML for a specific button."""
    try:
        device_config = current_app.config['DEVICE_CONFIG']
        
        # Validate plugin exists
        plugin_config = device_config.get_plugin(plugin_id)
        if not plugin_config:
            return "Plugin not found", 404
        
        # Get plugin instance
        from plugins.plugin_registry import get_plugin_instance
        plugin = get_plugin_instance(plugin_config)
        
        # Get template parameters
        template_params = plugin.generate_settings_template()
        
        # Add button-specific context
        template_params['button_name'] = button_name
        template_params['button_prefix'] = f"{button_name}_plugin_"
        
        # Get current button configuration if it exists
        button_config = device_config.get_config("button_config", {})
        current_settings = button_config.get(button_name, {}).get("plugin_settings", {})
        template_params['current_settings'] = current_settings
        
        # Render the plugin's settings template with button-specific modifications
        return render_template(f'{plugin_id}/settings.html', plugin=plugin_config, **template_params)
        
    except Exception as e:
        logger.error(f"Error rendering plugin settings HTML for {plugin_id}: {e}")
        return f"Error loading plugin settings: {str(e)}", 500
def reset_button_config():
    """Reset button configuration to defaults."""
    try:
        device_config = current_app.config['DEVICE_CONFIG']
        
        # Default configuration
        default_config = {
            "SW_A": {
                "action_type": "plugin_refresh",
                "plugin_id": "comic",
                "plugin_settings": {"comic": "XKCD"}
            },
            "SW_B": {
                "action_type": "plugin_refresh",
                "plugin_id": "comic",
                "plugin_settings": {"comic": "Saturday Morning Breakfast Cereal"}
            },
            "SW_C": {
                "action_type": "plugin_refresh",
                "plugin_id": "comic",
                "plugin_settings": {"comic": "Dinosaur Comics"}
            },
            "SW_D": {
                "action_type": "plugin_refresh",
                "plugin_id": "comic",
                "plugin_settings": {"comic": "Cyanide & Happiness"}
            }
        }
        
        device_config.update_value("button_config", default_config, write=True)
        
        logger.info("Button configuration reset to defaults")
        return jsonify({"success": True, "message": "Button configuration reset to defaults"})
        
    except Exception as e:
        logger.error(f"Error resetting button configuration: {e}")
        return jsonify({"error": f"Failed to reset configuration: {str(e)}"}), 500

@buttons_bp.route('/buttons/test/<button_name>', methods=['POST'])
def test_button(button_name):
    """Test a button configuration by triggering its action."""
    try:
        device_config = current_app.config['DEVICE_CONFIG']
        refresh_task = current_app.config['REFRESH_TASK']
        
        button_config = device_config.get_config("button_config", {})
        config = button_config.get(button_name)
        
        if not config:
            return jsonify({"error": f"No configuration found for button {button_name}"}), 400
        
        # Import here to avoid circular imports
        from refresh_task import ManualRefresh
        
        action_type = config.get("action_type", "plugin_refresh")
        
        if action_type == "plugin_refresh":
            plugin_id = config.get("plugin_id")
            plugin_settings = config.get("plugin_settings", {})
            
            if not plugin_id:
                return jsonify({"error": f"No plugin_id configured for button {button_name}"}), 400
            
            # Verify plugin exists
            plugin_config = device_config.get_plugin(plugin_id)
            if not plugin_config:
                return jsonify({"error": f"Plugin '{plugin_id}' not found"}), 400
            
            refresh_action = ManualRefresh(plugin_id, plugin_settings)
            refresh_task.manual_update(refresh_action)
            
            logger.info(f"Test refresh triggered for button {button_name} with plugin '{plugin_id}'")
            return jsonify({"success": True, "message": f"Button {button_name} test completed successfully"})
        else:
            return jsonify({"error": f"Unknown action_type '{action_type}'"}), 400
            
    except Exception as e:
        logger.error(f"Error testing button {button_name}: {e}")
        return jsonify({"error": f"Failed to test button: {str(e)}"}), 500