/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const dao = new Dao(db)
  const collection = dao.findCollectionByNameOrId("0jnu2vp85yhj5x6")

  // update
  collection.schema.addField(new SchemaField({
    "system": false,
    "id": "tbn6befg",
    "name": "realized",
    "type": "number",
    "required": false,
    "presentable": false,
    "unique": false,
    "options": {
      "min": null,
      "max": null,
      "noDecimal": false
    }
  }))

  return dao.saveCollection(collection)
}, (db) => {
  const dao = new Dao(db)
  const collection = dao.findCollectionByNameOrId("0jnu2vp85yhj5x6")

  // update
  collection.schema.addField(new SchemaField({
    "system": false,
    "id": "tbn6befg",
    "name": "realized",
    "type": "number",
    "required": true,
    "presentable": false,
    "unique": false,
    "options": {
      "min": null,
      "max": null,
      "noDecimal": false
    }
  }))

  return dao.saveCollection(collection)
})
