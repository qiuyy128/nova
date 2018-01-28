// var $ = document.querySelector.bind(document);
//
// document.addEventListener('DOMContentLoaded', () => {
//
//   $('#open').addEventListener('click', () => {
//     var input = document.createElement('input');
//     input.type = 'file';
//     input.addEventListener('change', (e) => {
//       var file = e.target.files[0];
//       $('#name').value = file.name;
//       $('#type').value = file.type;
//       var reader = new FileReader();
//       reader.addEventListener('load', () => {
//         $('#content').value = reader.result;
//       });
//       reader.readAsText(file);
//     });
//     document.body.appendChild(input);
//     input.click();
//     input.parentElement.removeChild(input);
//   });
//
//   $('#save').addEventListener('click', () => {
//     var a = document.createElement('a');
//     a.download = $('#name').value;
//     a.type = $('#type').value;
//     a.href = 'data:text/plain;base64,' + window.btoa($('#content').value);
//     document.body.appendChild(a);
//     a.click();
//     a.parentElement.removeChild(a);
//   });
// });
