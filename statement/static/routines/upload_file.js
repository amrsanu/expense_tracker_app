// Function to select/deselect all checkboxes
function toggle(source) {
    var checkboxes = document.getElementsByName('file');
    for(var i=0, n=checkboxes.length;i<n;i++) {
      checkboxes[i].checked = source.checked;
    }
  }
  