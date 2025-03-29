# %%

import fitz
import os

import csv
import pandas as pd

import pprint

import tqdm


import json

import time

# %%
class extract_project:
    def  __init__(self,input_path,output_path,templatepath,quantiles,redaction_search_string,stutter_text_pixel_var,csv_exports,json_exports):
        self.input_path = input_path
        self.output_path = output_path
        self.templatepath = templatepath
        self.quantiles = quantiles
        self.redaction_search_string = redaction_search_string
        self.stutter_text_pixel_var = stutter_text_pixel_var
        self.csv_exports = csv_exports
        self.json_exports = json_exports



    def fix_stutter_text(self,word_dict):
        # print("fix stutter text")

        keys_to_delete_list=[]

        #### loop through word dictionary

        for key, value in word_dict.items():
            
            ### if we already marked the key for deletion, skip this iteration
            if key in keys_to_delete_list:
                continue


            ### get all keys where the word is the same, the coordiantes are close, and the key is not the current key

            x0 = value[0]
            y0 = value[1]
            x1 = value[2]
            y1 = value[3]
            word = value[4]

            cur_dupe_key_list = [k for k,v in word_dict.items()
                                if (word == v[4]) and
                                (key != k) and
                                (abs(x0-v[0])<=self.stutter_text_pixel_var) and
                                (abs(y0-v[1])<=self.stutter_text_pixel_var) and                                 
                                (abs(x1-v[2])<=self.stutter_text_pixel_var) and
                                (abs(y1-v[3])<=self.stutter_text_pixel_var)                                                              
                                ]
            
            ### update the keys to delete list
            keys_to_delete_list.extend(cur_dupe_key_list)


        #### remove the items from the dictionary if they're present in the keys_to_delete list
        for delkey in keys_to_delete_list:
            del word_dict[delkey]

        return word_dict









    ######################################################################################
    def get_word_dict(self,page):

        words = page.get_text("words")
        words ={k:v for k,v in enumerate(words)}

        return words
    
    ######################################################################################
    def determine_rows(self,word_dict):

        temp_word_dict = word_dict.copy()


        #### create a blank all rows list
        all_rows_list =[]

        ################ while temp_word_dict is not empty

        while temp_word_dict:

            ####  find the min of y0 in the temp dict
            minx0 = min([v[0] for v in temp_word_dict.values()])
            # print(miny0)
            # print(type(miny0))

            ##### create a dictinary of these left most words
            left_most_words = {k:v for k,v in temp_word_dict.items() if v[0] == minx0}
            ### delete the leftmost words
            for delkey in [k for k in left_most_words.keys()]:
                del temp_word_dict[delkey]


        ##### for each leftmost word:
            for k,v in left_most_words.items():


                ### create blank cur row dict
                cur_row ={}
                # add the leftmost word to the current row dict
                cur_row[k] = v

                #### find the other words in the temp_word_dict that line up with the leftmost word. Allow for a small variance?

                ##### y ceiling should be y1-((y1 - y0)/quantiles)
                y_ceiling = v[3]-((v[3]-v[1])/self.quantiles)
                # print(f"ceiling:{y_ceiling}")

                ### y floor should be y0 + ((y1-y0)/quantiles)
                y_floor = v[1]+((v[3]-v[1])/self.quantiles)
                # print(f"floor:{y_floor}")

                ##### line definition

                other_words ={}
                for ok, ov in temp_word_dict.items():

                    midpoint = (ov[1]+ov[3])/2

                    if y_ceiling > midpoint and y_floor < midpoint:

                        other_words[ok]=ov


                #### add the other words in the row to the cur_row_list(extend)
                cur_row.update(other_words)

                #### remove the other words from the temp_word_dict

                for del_key in other_words.keys():
                    del temp_word_dict[del_key]


                # convert the current dictionary values to a list
                cur_row_list = list(cur_row.values())


                # sort the current row list by x0
                cur_row_list = sorted(cur_row_list,key = lambda x:x[0])


                ### add the current row list to the all rows list

                all_rows_list.append(cur_row_list)


        ### sort all rows by the max of y0
        all_rows_list = sorted(all_rows_list,key=lambda x:max(y[3] for y in x))

        return all_rows_list
    ######################################################################################
    def split_to_columns(self,words_list,col_location_dict):

        #### create list of empty dictionaries to export
        out_dict ={k:[] for k in col_location_dict.keys()}


        for key,value in col_location_dict.items():

            for row in words_list:
                #### if any words are in range
                if any([(value[0]<=word[0]<=value[1]) for word in row]):
                    ######### append those raw words
                    out_dict[key].append(" ".join([word[4] for word in row if (value[0]<=word[0]<=value[1])]))
                else:
                    ### append a null string
                    out_dict[key].append(" ".strip())



        #### add the raw string as a column to the out dictionary


        out_dict["Data"] = [" ".join(word[4] for word in row)+" _" for row in words_list]


        #### sort the out dictionary

        out_dict = {k: out_dict[k] for k in sorted(out_dict, key=lambda x: x != "Data")}


        return out_dict
    ######################################################################################


    def read_template_delimiters(self,file):

        current_template_path = os.path.join(self.templatepath,file)

        search_results = ""

        out_dict = {}

        ##### read the template page
        with fitz.open(current_template_path) as template_doc:

            page = template_doc[0]

            search_results = page.search_for(self.redaction_search_string)

            # pprint.pprint(search_results)

        ### sort the search results
        search_results = sorted(search_results, key = lambda rect:(rect.x0,rect.x1))
        # pprint.pprint(search_results)


        ##### generate dictionary of min and max ranges for each column
        prior_cutoff = 0
        for index, rectangle in enumerate(search_results):

            x0,y0,x1,y1 = rectangle

            current_label = "Data "+str(index)
            current_cutoff = (x1+x0)/2


            out_dict.update({current_label:(prior_cutoff,current_cutoff)})


            prior_cutoff = current_cutoff

        return out_dict



    def draw_line_on_page(self,page,template_delimiters):
        page_height = page.rect.height
        for _, x_coor in template_delimiters.values():
            page.draw_line((x_coor, 0), (x_coor, page_height), color=(1, 0, 0),width=0.5)

        return page


    def file_level_processing(self,current_path):
            
        df = pd.DataFrame()

        df_list =[]
        
        ##### no extension
        file_name =os.path.splitext(os.path.split(current_path)[-1])[0]
    


        #### with extension

        file = os.path.basename(current_path)



        ###### get the delimiters

        template_delimiters = self.read_template_delimiters(file)

        

        with fitz.open(current_path) as doc:
                
            for pagenum, page in tqdm.tqdm(enumerate(doc),total = doc.page_count,desc=file_name):
                # print(page.rotation)


                #### clean the page do deal with Q wrapping issue
                page.wrap_contents()


                ### get the word dictionaries
                word_dict = self.get_word_dict(page)


                ## fix stutter text issue
                word_dict = self.fix_stutter_text(word_dict=word_dict)




                #### testing(export json dictionary)

                if self.json_exports:
                    with open(os.path.join(self.output_path,file+"-"+str(pagenum)+".json"),"w") as json_file:
                        json.dump(word_dict,json_file, indent=4)
                


                ##### determine which words belong on which rows
                words_list = self.determine_rows(word_dict)

                ### split the data into columns
                words_dict =self.split_to_columns(words_list,template_delimiters)

                #### couvert the dictionary into a data frame
                sub_df = pd.DataFrame(words_dict)

                ##### convert the data to strings
                for colnam in sub_df.columns:
                    # print(colnam)
                    sub_df[colnam]=sub_df[colnam].astype(str)

                #### add the page number and reorder the columns
                sub_df["PageNum"]=pagenum+1
                new_order = ["PageNum"] + [col for col in sub_df.columns if col != "PageNum"]
                sub_df=sub_df[new_order]



                #### add the file name to the df the reorder it
                sub_df["File"]=file_name
                new_order = ['File'] + [col for col in sub_df.columns if col != 'File']
                sub_df=sub_df[new_order]



                df_list.append(sub_df)


                ###### draw a line on the out put page
                page = self.draw_line_on_page(page,template_delimiters)
            
            doc.save(os.path.join(self.output_path,file))
        print(f"Combining dataframe pages for file: {file_name}")
        df = pd.concat(df_list,ignore_index=True)


        if self.csv_exports:
            print(f"Exporting to CSV:{file_name}")
            df.to_csv(os.path.join(self.output_path,file_name+".csv"),index_label="Index")

            
        else:
        #### to excel could be really slow for big files
            print(f"Exporting to Excel: {file_name}")
            df.to_excel(os.path.join(self.output_path,file_name+".xlsx"),index_label="Index")

        return df
    ######################################################################################


    #### not using this here, importing this function
    def peel_first_page_templates(self):

        ### make sure the template path exists
        if not os.path.exists(self.templatepath):
            os.makedirs(self.templatepath)


        for file in tqdm.tqdm(os.listdir(self.input_path)):
            inpath = os.path.join(self.input_path,file)
            outpath = os.path.join(self.templatepath,file)

            #### open the file and get the first page

            with fitz.open(inpath) as indoc:

                outdoc = fitz.open()

                outdoc.insert_pdf(indoc,from_page=0,to_page=0)

                outdoc.save(outpath)

        print("Done")
        time.sleep(1)



    def main(self):
        #### make sure the output folder exists
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

        df_list =[]


        for file in os.listdir(self.input_path):
    
            current_path = os.path.join(self.input_path,file)
            df = self.file_level_processing(current_path)


            df_list.append(df)

            print(f"Dataframe Length for {file} : {len(df)}")
            print("----------------------------------------------")

        # df = pd.concat(df_list)
        # print(f"main len{len(df)}")

        return df
    ######################################################################################



# %%


# %%
if __name__=="__main__":


    parent_folder = os.path.abspath('')



    #### don't explicitly define these paths, use relative paths to the CWD folder
    extraction = extract_project(

        

        input_path = os.path.join(parent_folder,"input"),
        output_path = os.path.join(parent_folder,"output"),
        templatepath = os.path.join(parent_folder,"template_pages"),
        quantiles=3,
        redaction_search_string = "@",
        stutter_text_pixel_var =1,
        csv_exports = False,
        json_exports = False

    )

    try:


        extraction.main()
    except Exception as e:
        print(e)



    # extraction.peel_first_page_templates()

# %%




