document.addEventListener('DOMContentLoaded', function() {
    var inputModelDefinitionSelect = document.getElementById('id_input_model_definition');
    var inputModelFieldSelect = document.getElementById('id_input_model_field');
    var outputModelDefinitionSelect = document.getElementById('id_output_model_definition');
    var outputModelFieldSelect = document.getElementById('id_output_model_field');

    function updateModelFields(modelDefinitionSelect, modelFieldSelect, modelFields) {
        modelFieldSelect.innerHTML = '';
        if (modelDefinitionSelect.value) {
            modelFields[modelDefinitionSelect.value].forEach(function(field) {
                var option = document.createElement('option');
                option.value = field.id;
                option.textContent = field.field_name;
                modelFieldSelect.appendChild(option);
            });
        }
    }

    inputModelDefinitionSelect.addEventListener('change', function() {
        updateModelFields(inputModelDefinitionSelect, inputModelFieldSelect, inputModelFields);
    });

    outputModelDefinitionSelect.addEventListener('change', function() {
        updateModelFields(outputModelDefinitionSelect, outputModelFieldSelect, outputModelFields);
    });

    updateModelFields(inputModelDefinitionSelect, inputModelFieldSelect, inputModelFields);
    updateModelFields(outputModelDefinitionSelect, outputModelFieldSelect, outputModelFields);
});