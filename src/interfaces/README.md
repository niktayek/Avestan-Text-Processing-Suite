# Interfaces

This directory contains the python interfaces for various 3rd-party software used in this project.

## CAB
CAB contains a large database of Avestan manuscripts, including their images and the transliteration of some pages. The images are stored in standard PNG or JPEG format, but the transliterations are provided in an XML format standardized by the CAB project. The `cab` folder contains the Python script to read that XML format and provide word-level access to transliteration (along with the address of that word in the manuscript).

## eScriptorium
eScriptorium is a web-based platform for the collaborative transcription of manuscripts. It provides a set of tools for the annotation and editing of text, as well as a framework for the integration of various OCR tools. In this project, we import CAB exports to eScriptorium, fix/add transliteration, export eScriptorium data (which is a combination of images and XMLs formatted according to the eScriptorium specifications), and used eScriptorium XMLs for further analysis or OCR training. The `escriptorium` folder contains the Python scripts to read eScriptorium XML files and provide a word-level access to transliteration (along with the address of that word in the manuscript).

## XML translator
Sometimes in this project we need to translate an eScriptorium XML to a CAB XML. The `xml_translator` folder contains the Python scripts to perform this translation.
