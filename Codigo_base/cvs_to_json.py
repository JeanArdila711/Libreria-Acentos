import pandas as pd

# Lee el archivo CSV desde la carpeta Taller_1, ignorando líneas problemáticas
data = pd.read_csv('Taller_1/books.csv', on_bad_lines='skip')

# Genera el archivo JSON en la misma carpeta
data.to_json('Taller_1/books.json', orient='records', force_ascii=False, indent=4)

print('Archivo JSON generado exitosamente en Taller_1/books.json (líneas problemáticas ignoradas).')
