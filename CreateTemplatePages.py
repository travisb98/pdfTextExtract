
##### importing the peel first page templates from the pdfTextExtract script
try:
    import os
    import pandas
    import fitz
    import time
    import pdfTextExtract
    import shutil



    if __name__=="__main__":

        parent_folder = os.path.abspath('')


        #### don't explicitly define these paths, use relative paths to the CWD folder
        extraction = pdfTextExtract.extract_project(

            

            input_path = os.path.join(parent_folder,"input"),
            output_path = os.path.join(parent_folder,"output"),
            templatepath = os.path.join(parent_folder,"template_pages"),
            quantiles=4,
            redaction_search_string = "@",
            stutter_text_pixel_var =1,
            csv_exports = False,
            json_exports = False
        )


        extraction.peel_first_page_templates()


        #### delete the py cache if it exits in the cwd

        if os.path.exists(os.path.join(parent_folder,"__pycache__")):
            shutil.rmtree(os.path.join(parent_folder,"__pycache__"))


    time.sleep(1)
except Exception as e:
    print("Error")
    print(e)
    time.sleep(5)